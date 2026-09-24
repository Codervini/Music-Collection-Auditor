import requests
from dotenv import dotenv_values
from pathlib import Path
from pprint import pprint
from mca.core.db_butler import ( insert_multiple_columns_data , fetch_id_by_value , get_all_values_of_a_column_in_tb ,
                                update_multiple_columns_data, get_all_values_of_multiple_column_in_tb) 
from schema.models.file_universe import *
from schema.lookup.file_universe_lookup import *
from mca.core.logger import set_logger
from mca_tools.utils import api_request_handler, coerce_to_date
import csv
from datetime import date
import time
import json
import ast
from mca_tools.cacher.api_cacher import *
import mca_tools.cacher.parsed_cacher as pc
from mca_tools.seeder_audit.audit_flusher import *
from mca_tools.seeder_audit.audit_writer import *
from mca_tools.seeder_audit.orphan_scanner import *
import inspect
CONFIG_CONSTANTS = dotenv_values(Path("config",".env"))
mb_header = {"User-Agent": f"{CONFIG_CONSTANTS["APP_NAME"]}/{CONFIG_CONSTANTS["VERSION"]} ( {CONFIG_CONSTANTS["CONTACT_EMAIL"]} )"}
logger = set_logger(__name__)
lastfm_api_key = CONFIG_CONSTANTS["LASTFM_API_KEY"]
lastfm_session = get_session("lastfm",60)
musicbrainz_session = get_session("musicbrainz",60)

def discover_artists_lastfm(artist_discovery_limit:int = 50) -> dict:
    artist_and_mbid = {}
    api = f"http://ws.audioscrobbler.com/2.0/?method=chart.gettopartists&api_key={lastfm_api_key}&format=json&limit={artist_discovery_limit}"
    data = api_request_handler(api,lastfm_session)
    for i in data["artists"]["artist"]:
        name = i.get("name","")
        artist_and_mbid[name] = i.get("mbid","")
    logger.info(f"Discovered {len(data)} artists")
    return artist_and_mbid

def discover_similar_artists_lastfm(artist,mbid = "",limit:int = 50):
    api = f"http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist=cher&api_key={lastfm_api_key}&format=json&limit={limit}&artist={artist}&mbid={mbid}"
    response = api_request_handler(api,lastfm_session)
    data = {}
    with open(file=Path("data","log",f"sussy similar artist seed {date.today()}.csv"), mode="a") as f:
        writer = csv.writer(f)
        for i in response["similarartists"]["artist"]:
            if i.get("name").find(" & ") == -1: 
                data[i.get("name")] = [i.get("mbid", ""),i.get("match","")]
            else:
                writer.writerow([i.get("name"),i.get("mbid", ""),i.get("match","")])
    logger.info(f"Discovered {len(data)} similar artists for {artist}")    
    return data
    

class SeedArtistsFamily:
    def __init__(self):
        self.artist_and_mbid = {}
        self._init_data()
        # self.id_tb_data = get_all_values_of_multiple_column_in_tb(Artists,["id","name","mbid"],"created_at")
        self.session = SESSION_MANAGER()

    def _init_data(self):
        self.id_tb_data = get_all_values_of_multiple_column_in_tb(Artists,["id","name","mbid"],"created_at")
    def _validate_artists_data_completion(self,id):
        data = get_all_values_of_multiple_column_in_tb(Artists,[ 'name', 'sort_name', 'type_id', 
                                                                'gender_id', 'mbid', 'isni', 'country_id', 'born_or_formed', 
                                                                'died_or_disbanded', 'disambiguation', 'raw_mb_response']
                                                                )
        for i in data:
            if not data[i]:
                return False
        return True 

    def seed_artists(self,artist_discovery_limit:int=50, similar_artist_discovery_limit:int=969):
        auditor = AuditWriter(self.session,seeder_name=inspect.currentframe().f_code.co_name)
        artist_and_mbid = discover_artists_lastfm(artist_discovery_limit)
        for name,mbid in artist_and_mbid.items():
            self.artist_and_mbid[mbid] = name
            pc.set("lastfm",mbid,{"name":name})
            inserted  = insert_multiple_columns_data(Artists,{"name":name,"mbid":mbid})
            if inserted:
                auditor.record(Artists.__tablename__,mbid,status="inserted")
            else:
                auditor.record(Artists.__tablename__,mbid,status="failed")

            similar_artists = discover_similar_artists_lastfm(name,mbid,similar_artist_discovery_limit)
            for name,v in similar_artists.items():
                print(name,"================",v)
                pc.set("lastfm",v[0],{"name":name})
                self.artist_and_mbid[v[0]] = name
                inserted  = insert_multiple_columns_data(Artists,{"name":name,"mbid":v[0]})
                if inserted:
                    auditor.record(Artists.__tablename__,v[0],status="inserted")
                else:
                    auditor.record(Artists.__tablename__,v[0],status="failed")
        auditor.finish()
    def seed_artist_props_musicbrainz(self):      
        auditor = AuditWriter(self.session,seeder_name=inspect.currentframe().f_code.co_name)
        data_counter = 0
        for id, name, mbid in self.id_tb_data:
            print(data_counter, " Now: ", mbid)
            try:
                parsed  = pc.get("musicbrainz",mbid)
                if parsed:
                    columns_data =  {   "isni": parsed["isni"],
                                        "sort_name":parsed["sort_name"],
                                        "type_id":parsed["type_id"],
                                        "born_or_formed": parsed["born_or_formed"],
                                        "died_or_disbanded": parsed["died_or_disbanded"],
                                        "gender_id": parsed["gender_id"],
                                        "country_id": parsed["country_id"],
                                        "disambiguation": parsed["disambiguation"],
                                        "raw_mb_response": parsed["raw_mb_response"]}
                    logger.debug("Fetched from cache: %s",mbid)
                    print("Fetched from cache: ",mbid)
                elif mbid: 
                    api = f"https://musicbrainz.org/ws/2/artist/{mbid}?fmt=json&inc=aliases+url-rels+tags+genres+annotation+ratings"
                    data = api_request_handler(api, musicbrainz_session, mb_header)
                    if data:
                        life_span = data.get("life-span", {})
                        columns_data =  {   "isni": (data["isnis"][0] if len(data["isnis"]) > 0 else ""),
                                            "sort_name":data.get("sort-name", ""),
                                            "type_id":fetch_id_by_value(ArtistTypeLookup,"alt_type_id",data.get("type-id")),
                                            "born_or_formed": coerce_to_date(life_span.get("begin", None)),
                                            "died_or_disbanded": coerce_to_date(life_span.get("end", None)),
                                            "gender_id": fetch_id_by_value(GenderLookup,"name", data.get("gender")),
                                            "country_id": fetch_id_by_value(CountryLookup, "alpha2", data.get("country", "Unknown")),
                                            "disambiguation": data.get("disambiguation", ""),
                                            "raw_mb_response": data
                                        }
                        pc.set("musicbrainz",mbid,columns_data)
                    else:
                        logger.warning("No results from MB for: %s",mbid)
                        print("No results from MB for: ",mbid)
                if columns_data:
                    columns_data["data_complete"] = True
                    for i in columns_data:
                        ignore  = {"died_or_disbanded", "disambiguation"}
                        if i not in ignore and not columns_data[i]:
                            columns_data["data_complete"] = False
                            break
                    updated = update_multiple_columns_data(Artists,"mbid",mbid,columns_data) 
                    if updated:
                        auditor.record(Artists.__tablename__,str(id),status="inserted")
                    else:
                        auditor.record(Artists.__tablename__,str(id),status="failed")
                    logger.info(f"UPDATED Artist {name} : {mbid} props ")    
                               
                columns_data = None
            except Exception as e:
                    logger.error("Failed for mbid %s: %s", mbid, e, exc_info=True)
                    raise e
            data_counter += 1
        auditor.finish(True)
        logger.info("%d of %d artist properties seeded succesfully",data_counter,len(self.artist_and_mbid))

    def seed_artist_aliases(self):
        auditor = AuditWriter(self.session,seeder_name=inspect.currentframe().f_code.co_name)
        alias_count = 0
        artist_count = 0
        empty_count = 0
        success_count = 0
        for id, name, mbid in self.id_tb_data:
            parsed =  pc.get("musicbrainz",mbid)
            # pprint(parsed)
            # time.sleep(2)
            
            if parsed and len(parsed["raw_mb_response"]["aliases"]) > 0:
                aliases = parsed["raw_mb_response"]["aliases"]
                for alias in aliases:
                    data = {"artist_id":fetch_id_by_value(Artists,"mbid",mbid),
                            "alias_type_id": fetch_id_by_value(AliasTypeLookup,"name",(alias.get("type") or "Unspecified").capitalize()),
                            "name":alias.get("name","Unknown"),
                            "sort_name":alias.get("sort-name","Unknown"),
                            "locale_id": fetch_id_by_value(LocaleLookup,"code",alias.get("locale",None)),
                            "is_primary": alias.get("primary",None)
                            }
                    # pprint(alias)
                    # pprint(data)
                    inserted = insert_multiple_columns_data(ArtistAliases,data)
                    if inserted:
                        auditor.record(ArtistAliases.__tablename__,str(id),status="inserted")
                    else:
                        auditor.record(ArtistAliases.__tablename__,str(id),status="failed")
                    alias_count+=1
                    pprint(f"{alias_count}/{len(aliases)} of {name}:{id} inserted")
                    logger.info(f"{alias_count}/{len(aliases)} of {name}:{id} inserted")
                success_count +=1
                logger.info("%d aliases of %s:%s  inserted succesfully",len(aliases),name,id)
            else:
                empty_count+=1
                logger.warning(f"No aliases of {name}:{id} found")
            alias_count = 0
            artist_count+=1
        # pprint(f"{artist_count}/{len(self.id_tb_data)} completed")
        auditor.finish(True)
        logger.info("%d of %d artist's aliases inserted succesfully",success_count,artist_count)
        logger.info("%d of %d artist's aliases not found",empty_count,artist_count)
    def seed_artist_link(self):
        auditor = AuditWriter(self.session,seeder_name=inspect.currentframe().f_code.co_name)
        # self._init_data()
        for id, name, mbid in self.id_tb_data:
            parsed = pc.get("musicbrainz",mbid)
            if parsed:
                relations = parsed["raw_mb_response"]["relations"]
                links_count = 0
                for link in relations:
                    # pprint(link)
                    links_count+=1
                    if link.get("target-type",None) == "url" and link["url"].get("resource"):
                        data = {"artist_id": id,
                                "link_type_id": (fetch_id_by_value(LinkTypeLookup,"alt_type_id",link.get("type-id")) or fetch_id_by_value(LinkTypeLookup,"name",link.get("type","").title())),
                                "url": link["url"].get("resource"), 
                        }
                        # pprint(data)
                        if not data["link_type_id"]:
                            insert_multiple_columns_data(LinkTypeLookup,{"name":link.get("type","").title(),
                                                                         "base_url":"/".join(data["url"].split("/")[:3]+[""]),   
                                                                         "ingestion_source":inspect.currentframe().f_code.co_name})
                            data["link_type_id"] = fetch_id_by_value(LinkTypeLookup,"name",link.get("type","").title())
                            logger.warning(f"New URL name found '{link.get("type","").title()}' for {name}:{id} and inserting new lookup record!")
                        inserted = insert_multiple_columns_data(ArtistLinks,data)
                        print(f"{links_count}/{len(relations)} links of {name} processed")
                        if inserted:
                            auditor.record(ArtistLinks.__tablename__,str(id),status="inserted")
                        else:
                            auditor.record(ArtistLinks.__tablename__,str(id),status="failed")
                    else:
                        logger.warning(f"{link} is not a valid link object for {name}:{id}")
                else:
                    logger.info(f"Processed {len(relations)} url link objects for {name}:{id}")
            else:
                logger.warning(f"No link found for {name}:{id}")
        auditor.finish()

class SeedWorksFamily():
    def __init__(self):
        self.session = SESSION_MANAGER()
        self.artist_tb_data = get_all_values_of_multiple_column_in_tb(Artists,["id","name","mbid"],"created_at")
        self.work_tb_data = get_all_values_of_multiple_column_in_tb(Works,["id","mbid","title","type_id","iswc","language_id"],"created_at") 
    def _get_work_data_from_mb(self,mbid,offset,limit=100):
        api = f"https://musicbrainz.org/ws/2/work?artist={mbid}&offset={offset}&limit={limit}&fmt=json"
        return api_request_handler(api, musicbrainz_session, mb_header)
    def seed_works_mb(self):
        auditor = AuditWriter(self.session,seeder_name=inspect.currentframe().f_code.co_name) 
        cumulative_works_fetch_count = 0
        try:
            for position, (id, name, mbid) in enumerate(self.artist_tb_data, start=1):
                logger.info(f"Processing artist {position}/{len(self.artist_tb_data)} | name={name} | id={id} | MBID={mbid}")
                if not mbid:
                    logger.warning(f"{name}:{id} has no mbid, skipping quering for works.")
                else:
                    logger.info(f"Beginning to process works of {name} | MBID={mbid}")
                    works = []
                    work_count = 0
                    try:
                        initial_data = self._get_work_data_from_mb(mbid,0)
                        cumulative_works_fetch_count +=1
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 404:
                            logger.warning(f"MusicBrainz artist MBID is invalid, recording for review | name={name} | MBID={mbid}")
                            # WIP: Handle such invalid cases by recording for future review
                            continue
                        raise 
                    works.extend([work for work in initial_data["works"]])
                    logger.info(f"Found {initial_data['work-count']} works of {name} | MBID={mbid}")
                    for offset in range(100,initial_data["work-count"],100):
                        succesive_data = self._get_work_data_from_mb(mbid,offset)
                        cumulative_works_fetch_count +=1
                        works.extend([work for work in succesive_data["works"]])
                    else:
                       logger.debug(f"Finished querying all works of {name} | MBID={mbid} | Total works={initial_data['work-count']}")
                    if initial_data["work-count"] == 0:
                        logger.info(f"No works found for {name} | MBID={mbid}; skipping processing")
                        continue
                    logger.info(f"Started processing {len(works)} works of {name} | MBID={mbid}")
                    for work in works:
                        work_count +=1
                        if work.get("title"):
                            data = {"title": work.get("title"),
                                    "type_id": fetch_id_by_value(WorkTypeLookup,"name", (work.get("type") or "").capitalize()),
                                    "iswc":work.get("iswcs"),
                                    "language_id": fetch_id_by_value(ISOLanguageLookup,"iso_639_3", work.get("language")),
                                    "mbid":work.get("id"),
                                    "disambiguation":work.get("disambiguation",None),
                                    "raw_mb_response":initial_data                            
                            }
                            inserted = insert_multiple_columns_data(Works,data) 
                            if inserted:
                                auditor.record(Works.__tablename__,str(id),status="inserted")
                            else:
                                auditor.record(Works.__tablename__,str(id),status="failed")
                        else:
                            logger.warning(f"Invalid work {work_count}/{len(works)}, skipping")  
                    else:
                        logger.info(f"Processed {work_count}/{len(works)} works of {name}:{id}")
                logger.info(f"Fetched works {cumulative_works_fetch_count} times for {position} artists as of now")
            else:
                logger.info(f"Works table is seeded succesfully for {len(self.artist_tb_data)} artists")
        except Exception as e:
            logger.critical(f"Exception occured for {name}:{id}: {e}",exc_info=True)
        auditor.finish()

    def seed_work_credits(self):
        auditor = AuditWriter(self.session,seeder_name=inspect.currentframe().f_code.co_name) 
        total_work_credits = 0
        # ["id","mbid","title","type_id","iswc","language_id"]
        for count , work in enumerate(self.work_tb_data,1):
            logger.info(f"Beginning to process {count}/{len(self.work_tb_data)} work for its credits")
            if not work[1]: # work["mbid"]
                logger.warning(f"{work[2]}:{work[0]} has no mbid, skipping quering for work credits.")
                continue
            work_credit_count = 0
            api = f"https://musicbrainz.org/ws/2/work/{work[1]}?inc=artist-rels&fmt=json"
            all_credits =  api_request_handler(api, musicbrainz_session, mb_header)
            if not all_credits:
                logger.warning(f" No work credits found for {work[2]}:{work[0]} | mbid={work[1]}; skipping")
                continue
            logger.info(f"Credits found for work name:{work[2]} | id:{work[0]} | mbid:{work[1]}, proceding to process")
            for count, credit in enumerate(all_credits["relations"],start=1):
                if not credit["artist"]["id"]:
                    logger.warning(f"{count}/{len(all_credits["relations"])} Work-Credit relation has no Artist MBID, skipping")
                    continue
                if not fetch_id_by_value(Artists,"mbid",credit["artist"]["id"]):
                    d = {
                        "name":credit["artist"]["name"],
                        "sort_name":credit["artist"]["sort-name"],
                        "type_id":fetch_id_by_value(ArtistTypeLookup,"alt_type_id",credit["artist"]["type-id"]),
                        "disambiguation": credit["artist"]["disambiguation"],
                        "country_id": fetch_id_by_value(CountryLookup, "alpha2", credit["artist"]["country"]),
                        "mbid":credit["artist"]["id"]
                    }
                    insert_multiple_columns_data(Artists,d)
                data = {
                    "work_id":work[0],
                    "artist_id":fetch_id_by_value(Artists,"mbid",credit["artist"]["id"]),
                    "role_id":fetch_id_by_value(ArtistRolesLookup,"name",(credit["type"] or "").lower()),
                    "credit_source_id":(fetch_id_by_value(CreditSourceLookup,"name",credit["source-credit"]) or None),
                    "credit_source_url": api,
                    # "credit_order": None,
                    "note": None
                }
                inserted = insert_multiple_columns_data(WorkCredits,data) 
                if inserted:
                    auditor.record(Works.__tablename__,str(id),status="inserted")
                    total_work_credits +=1
                else:
                    auditor.record(Works.__tablename__,str(id),status="failed")
                
            logger.info(f" {total_work_credits} Work Credits for {len(self.work_tb_data)} seeded succesfully.")

        auditor.finish()

class SeedRecordingsFamily():
    def __init__(self):
        self.session = SESSION_MANAGER()
        self.artist_tb_data = get_all_values_of_multiple_column_in_tb(Artists,["id","name","mbid"],"created_at")
        self.work_tb_data = get_all_values_of_multiple_column_in_tb(Works,["id","mbid","title"],"created_at")
    def _mb_api_handler(self, entity: str, mbid: str , offset: int, limit:int=100):
        api = f"https://musicbrainz.org/ws/2/recording?{entity}={mbid}&offset={offset}&limit={limit}&fmt=json"
        print(api)
        return api_request_handler(api, musicbrainz_session, mb_header)

    def _get_all_recordings_using_artist_or_work_mbid(self,artist_mbid: str = None, work_mbid: str = None):
        if artist_mbid:
            entity = "artist"
            mbid = artist_mbid
        elif work_mbid:
            entity = "work"
            mbid = work_mbid
        else:
            logger.error("No MBID provided!")
            return
        recordings = []
        first_batch = self._mb_api_handler(entity,mbid,0,100)
        recordings.extend(first_batch.get("recordings"))
        if first_batch.get("recording-count") > 100:
            for offset in range(100,first_batch.get("recording-count"),100):
                next_batch = self._mb_api_handler(entity,mbid,offset,100)
                recordings.extend(next_batch.get("recordings"))

        return recordings
    
    def _seed_recordings(self,recordings: list[dict], auditor: AuditWriter):
        for record in recordings:
            if not record.get("id"):
                continue
            api = f"https://musicbrainz.org/ws/2/recording/{record.get("id")}?inc=isrcs+artist-credits+recording-rels+label-rels+artist-rels+work-rels&fmt=json"
            record_details = api_request_handler(api, musicbrainz_session, mb_header)
            data = {}

            for relation in record_details["relations"]:
                if relation.get("target-type") == "work":
                    if not fetch_id_by_value(Works,"mbid", relation["work"]["id"]):
                        # If such work doesn't exist in Works table
                        work_data = {
                            "title": relation["work"].get("title"),
                            "type_id": fetch_id_by_value(WorkTypeLookup,"name",(relation["work"].get("type") or "").capitalize()),
                            "iswc":relation["work"].get("iswcs"),
                            "language_id": fetch_id_by_value(ISOLanguageLookup,"iso_639_3", relation["work"].get("language")),
                            "mbid":relation["work"].get("id"),
                            "disambiguation":relation["work"].get("disambiguation",None),
                            "raw_mb_response":relation["work"]                            
                        } 
                        insert_multiple_columns_data(Works,work_data)
                    data["work_id"] =  fetch_id_by_value(Works,"mbid", relation["work"]["id"])
                elif relation.get("target-type") == "recording":
                    # Insert related recordings data of the current recording to tb
                    related_recording = {
                        "work_id": None,
                        "version_type_id": fetch_id_by_value(VersionTypeLookup,"alt_type_id", relation.get("type-id")),
                        "official_title": relation["recording"].get("title"),
                        "version_name": None,
                        "display_title": None,
                        "duration_ms": relation["recording"].get("length"),
                        "acoustid_fingerprint": None,
                        "acoustid_mbid": None,
                        "mb_recording_id": relation["recording"].get("id"),
                        "isrc": relation["recording"].get("isrcs"),
                        "language_id": None,
                        "raw_mb_response": relation,
                    }
                    insert_multiple_columns_data(Recordings,related_recording)

                    # Insert the artist credits for the above recording
                    # TBD
                elif relation.get("target-type") == "artist":
                    # Handled with seperate method
                    pass 
            data.update( (k,v) for k,v in {
                    # "version_type_id": fetch_id_by_value(VersionTypeLookup,"alt_type_id", relation.get("type-id")),
                    "official_title": record_details.get("title"),
                    "version_name": None,
                    "display_title": None,
                    "duration_ms": record_details.get("length"),
                    "acoustid_fingerprint": None,
                    "acoustid_mbid": None,
                    "mb_recording_id": record_details.get("id"),
                    "isrc": record_details.get("isrcs"),
                    "language_id": None,
                    "raw_mb_response": record_details,
                }.items())
            insert_multiple_columns_data(Recordings,data)
            
            
        
        
    def seed_recordings_from_works_mb(self):
        auditor = AuditWriter(self.session,seeder_name=inspect.currentframe().f_code.co_name) 
        logger.info(f"---------------------------Starting to seed recordings for {len(self.work_tb_data)} Works using Musicbrainz---------------------------")
        for work_count, (id, mbid, title) in enumerate(self.work_tb_data,1):
            logger.info(f" Beginning to process mbid: {mbid}.")
            recordings = self._get_all_recordings_using_artist_or_work_mbid(work_mbid=mbid)
            self._seed_recordings(recordings,auditor)
            

    def seed_recordings_from_artists_mb(self):
        auditor = AuditWriter(self.session,seeder_name=inspect.currentframe().f_code.co_name) 
        logger.info(f"---------------------------Starting to seed recordings for {len(self.work_tb_data)} Artists using Musicbrainz---------------------------")
        for artist_count, (id,name,mbid) in enumerate(self.artist_tb_data,1):
            logger.info(f" Beginning to process mbid: {mbid}.")
            recordings = self._get_all_recordings_using_artist_or_work_mbid(artist_mbid=mbid)
            self._seed_recordings(recordings,auditor)


            
            


# SeedArtistsFamily().seed_artists(10,1)       
# SeedArtistsFamily().seed_artist_props_musicbrainz()  
# SeedArtistsFamily().seed_artist_aliases()     
# SeedArtistsFamily().seed_artist_link()     
# SeedWorksFamily().seed_works_mb()
# SeedWorksFamily().seed_work_credits()
SeedRecordingsFamily().seed_recordings_from_works_mb()


