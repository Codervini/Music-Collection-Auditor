from dotenv import dotenv_values
from pathlib import Path
from pprint import pprint
from mca.core.db_butler import insert_multiple_columns_data , fetch_id_by_value
# from schema.models.file_universe import Artists
from schema.lookup.file_universe_lookup import *
from mca.core.logger import set_logger
from mca_tools.utils import api_request_handler
import csv
from babel.localedata import locale_identifiers
from babel.core import Locale, UnknownLocaleError
from mca_tools.cacher.api_cacher import get_session

CONFIG_CONSTANTS = dotenv_values(Path("config",".env"))
logger = set_logger(__name__)
lastfm_api_key = CONFIG_CONSTANTS["LASTFM_API_KEY"]
restcountries_session = get_session("restcountries",60)


def seed_country_lookup_restcountries():
    # 254 Countries
    offset = [0,100,200]
    limit = [100,100,54]
    for i in range(0, len(offset)):
        api = f"https://api.restcountries.com/countries/v5?limit={limit[i]}&offset={offset[i]}&response_fields=names,codes,region,subregion,continents&response_fields_omit=names.translations"
        data = api_request_handler(api,restcountries_session,{'Authorization': f'Bearer {CONFIG_CONSTANTS["REST_COUNTRIES_API_KEY"]}'})
        for i in range(0,data["data"]["meta"]["count"]):
            columns_data =  {"name":data["data"]["objects"][i]["names"]["common"],
                            "official_name": data["data"]["objects"][i]["names"]["official"],
                            "alpha2":data["data"]["objects"][i]["codes"]["alpha_2"],
                            "alpha3": data["data"]["objects"][i]["codes"]["alpha_3"],
                            "numeric_code":data["data"]["objects"][i]["codes"]["ccn3"],
                            "continent":", ".join(data["data"]["objects"][i]["continents"])
                            }
            insert_multiple_columns_data(CountryLookup,columns_data)
    else:
        logger.info(" Country Lookup Seeded")

def seed_gender_lookup():
    genders = [
    ("Male",                "Identifies as male"),
    ("Female",              "Identifies as female"),
    ("Trans Male",          "Identifies as trans male"),
    ("Trans Female",        "Identifies as trans female"),
    ("Non-binary",          "Identifies outside the male/female binary"),
    ("Genderqueer",         "Identifies as genderqueer or gender non-conforming"),
    ("Genderfluid",         "Gender identity that shifts over time"),
    ("Agender",             "Identifies as having no gender"),
    ("Bigender",            "Identifies as two genders"),
    ("Androgyne",           "Identifies as androgynous or between genders"),
    ("Two-Spirit",          "Indigenous North American third-gender identity"),
    ("Intersex",            "Born with variations in sex characteristics"),
    ("Boy Group",           "All-male musical group"),
    ("Girl Group",          "All-female musical group"),
    ("Mixed Group",         "Mixed-gender musical group"),
    ("Trans Male Group",    "Group identifying as trans male"),
    ("Trans Female Group",  "Group identifying as trans female"),
    ("Mixed Trans Group",   "Group with mixed trans gender identities"),
    ("Not Applicable",      "Entity for which gender is not applicable"),
    ("Unknown",             "Gender not known or not recorded"),
    ("Prefer Not to Say",   "Gender withheld by choice"),
    ]
    for i in genders:
        insert_multiple_columns_data(GenderLookup,{"name":i[0],"description":i[1]})
    logger.info(" Gender Lookup Seeded")

def seed_artist_type_lookup():
    artist_types = [
        ("Person","A single individual artist","b6e035f4-3ce9-331c-97df-83397230b0df","MusicBrainz"),
        ("Group","A band, ensemble, or musical group","e431f5f6-b5d2-343d-8b36-72607fffb74b","MusicBrainz"),
        ("Choir","A vocal ensemble or chorus","6124967d-7e3a-3eba-b642-c9a2ffb44d94","MusicBrainz"),
        ("Orchestra","A large classical or symphonic ensemble","a0b36c92-3eb1-3839-a4f9-4799823f54a5","MusicBrainz"),
        ("Character","A fictional or animated character","5c1375b0-f18d-3db7-a164-a49d7a63773f","MusicBrainz"),
        ("Other","An artist type that does not fit standard categories","ac897045-5043-3294-969b-187360e45d86","MusicBrainz"),
        ("Unknown","Artist type not known or not recorded",None,"Codervini"),
    ]
    for i in artist_types:
        insert_multiple_columns_data(ArtistTypeLookup,{"name":i[0],"description":i[1],"alt_type_id":i[2],"ingestion_source":i[3]})
    logger.info(" Artist Type Lookup Seeded")

def seed_alias_types_lookup():
    alias_types = [
    ("Artist Name",       "An alternative name the artist performs or is known under"),
    ("Legal Name",        "The official birth or legal name, e.g. Stefani Germanotta → Lady Gaga"),
    ("Search Hint",       "A misspelling or common variation to aid search, e.g. Led Zepplin"),
    ("Stage Name",        "A performance name adopted for public use, distinct from legal name"),
    ("Nickname",          "An informal name given by fans, peers or media, e.g. The Boss, The King"),
    ("Alter Ego",         "A distinct persona adopted for a specific creative project, e.g. Ziggy Stardust"),
    ("Abbreviation",      "A shortened form of the artist name, e.g. JT for Justin Timberlake"),
    ("Transliteration",   "A phonetic rendering into another script, e.g. Чайковский → Tchaikovsky"),
    ("Translation",       "A meaning-based rendering into another language"),
    ("Contractual Alias", "A name used to bypass label or contractual restrictions"),
    ("Collaboration Name","A name used specifically for a joint project or group effort"),
    ("Birth Name",        "The name given at birth, before any legal or stage name change"),
    ("Collective Name",   "A shared name used by a group or rotating set of artists as one identity"),
    ("Unspecified",       "Alias type not yet determined — assign a specific type after research"),
    ]
    for i in alias_types:
            insert_multiple_columns_data(AliasTypeLookup,{"name":i[0],"description":i[1]})
    logger.info(" Alias Type Lookup Seeded")


def seed_locale_lookup():
    rtl_scripts = {"Arab", "Hebr", "Thaa", "Tfng", "Syrc", "Nkoo", "Adlm"}
    for locale_str in locale_identifiers():
        try:
            loc = Locale.parse(locale_str, sep="_")
            script  = str(loc.script)    if loc.script    else None
            region  = str(loc.territory) if loc.territory else None
            insert_multiple_columns_data(LocaleLookup,{
                "code":          locale_str,
                "language_code": str(loc.language),
                "region_code":   region,
                "script_code":   script,
                "display_name":  loc.get_display_name("en"),
                "is_rtl":        script in rtl_scripts if script else False,
            })
        except UnknownLocaleError:
            continue
    logger.info(" Locale Lookup Seeded")

def seed_link_types_lookup():
    link_types = [

    # Official
    ("Official Homepage","https://","Artist's official website","fe33d22f-c3b0-4d68-bd53-a856badf2b15","MusicBrainz"),
    ("Official Store","https://","Official merch or music store",None,"Codervini"),

    # Social Networks
    ("Facebook","https://www.facebook.com/","Facebook page or profile",None,"Codervini"),
    ("Instagram","https://www.instagram.com/","Instagram profile", None,"Codervini"),
    ("Twitter","https://twitter.com/","Twitter/X profile",None,"Codervini"),
    ("TikTok","https://www.tiktok.com/@","TikTok profile",None,"Codervini"),
    ("Myspace","https://myspace.com/","Myspace page","bac47923-ecde-4b59-822e-d08f0cd10156","MusicBrainz"),
    ("SoundCloud","https://soundcloud.com/","SoundCloud profile","89e4a949-0976-440d-bda1-5f772c1e5710","MusicBrainz"),
    ("Snapchat","https://www.snapchat.com/add/","Snapchat profile",None,"Codervini"),
    ("Threads","https://www.threads.net/@","Threads profile",None,"Codervini"),
    ("Bluesky","https://bsky.app/profile/","Bluesky profile",None,"Codervini"),
    ("Mastodon","https://","Mastodon profile",None,"Codervini"),
    ("Tumblr","https://","Tumblr blog",None,"Codervini"),

    # Video
    ("YouTube","https://www.youtube.com/","Official YouTube channel","6a540e5b-58c6-4192-b6ba-dbc71ec8fcf0","MusicBrainz"),
    ("YouTube Music","https://music.youtube.com/","YouTube Music channel","631712a0-7525-42ba-b7a3-605aa7a238c4","MusicBrainz"),
    ("Vimeo","https://vimeo.com/","Vimeo channel",None,"Codervini"),

    # Streaming
    ("Spotify","https://open.spotify.com/artist/","Spotify artist page",None,"Codervini"),
    ("Apple Music","https://music.apple.com/","Apple Music artist page","64785d6c-2eeb-4f86-9418-b6c2d6c53c13","MusicBrainz"),
    ("Tidal","https://tidal.com/browse/artist/","Tidal artist page", None,"Codervini"),
    ("Deezer","https://www.deezer.com/en/artist/","Deezer artist page",None,"Codervini"),
    ("Amazon Music","https://music.amazon.com/artists/","Amazon Music artist page",None,"Codervini"),
    ("Pandora","https://www.pandora.com/artist/","Pandora artist page",None,"Codervini"),

    # Purchase / Download
    ("Bandcamp","https://","Bandcamp artist page","c550166e-0548-4a18-b1d4-e2ae423a3e88","MusicBrainz"),
    ("CD Baby","https://store.cdbaby.com/Artist/","CD Baby artist page","4c21e5f5-2960-4abc-88a1-62ce491bb96e","MusicBrainz"),
    ("iTunes","https://music.apple.com/","iTunes artist page",None,"Codervini"),
    ("Purchase Download","https://","Page where music can be purchased for download","f8319a2f-f824-4617-81c8-be6560b3b203","MusicBrainz"),
    ("Purchase Mail Order","https://","Page where music can be purchased by mail order","611b1862-67af-4253-a64f-34adba305d1d","MusicBrainz"),
    ("Free Download","https://","Page where music can be downloaded for free","34ae77fe-defb-43ea-95d4-63c7540bac78","MusicBrainz"),
     ("Free Streaming","https://","Page where music can be streamed for free","769085a1-c2f7-4c24-a532-2375a77693bd","MusicBrainz"),

    # Databases / Reference
    ("MusicBrainz","https://musicbrainz.org/artist/","MusicBrainz artist page",None,"Codervini"),
    ("Discogs","https://www.discogs.com/artist/","Discogs artist page","04a5b104-a4c2-4bac-99a1-7b837c37d9e4","MusicBrainz"),
    ("Last.fm","https://www.last.fm/music/","Last.fm artist page","08db8098-c0df-4b78-82c3-c8697b4bba7f","MusicBrainz"),
    ("AllMusic","https://www.allmusic.com/artist/","AllMusic artist page","6b3e3c85-0002-4f34-aca6-80ace0d7e846","MusicBrainz"),
    ("Wikidata","https://www.wikidata.org/wiki/","Wikidata entity page","689870a4-a1e4-4912-b17f-7b2664215698","MusicBrainz"),
    ("Wikipedia","https://en.wikipedia.org/wiki/","Wikipedia article","29651736-fa6d-48e4-aadc-a557c6add1cb","MusicBrainz"),
    ("IMDb","https://www.imdb.com/name/","IMDb page","94c8b0cc-4477-4106-932c-da60e63de61c","MusicBrainz"),
    ("IMSLP","https://imslp.org/wiki/","IMSLP page for classical works","8147b6a2-ad14-4ce7-8f0a-697f9a31f68f","MusicBrainz"),
    ("SecondHandSongs","https://secondhandsongs.com/artist/","SecondHandSongs page","79c5b84d-a206-4f4c-9832-78c028c312c3","MusicBrainz"),
    ("Setlist.fm","https://www.setlist.fm/setlists/","Setlist.fm artist page","bf5d0d5e-27a1-4e94-9df7-3cdc67b3b207","MusicBrainz"),
    ("Songkick","https://www.songkick.com/artists/","Songkick artist page","aac9c4bc-a5b9-30b8-9839-e3ac314c6e58","MusicBrainz"),
    ("Bandsintown","https://www.bandsintown.com/","Bandsintown artist page","ea45ed3d-2d5e-456e-8c32-94b6f51426e2","MusicBrainz"),
    ("VGMdb","https://vgmdb.net/artist/","VGMdb page for video game/anime music artists","0af15ab3-c615-46d6-b95b-a5fcd2a92ed9","MusicBrainz"),
    ("VIAF","https://viaf.org/viaf/","Virtual International Authority File ID","e8571dcc-35d4-4e91-a577-a3382fd84460","MusicBrainz"),
    ("CPDL","https://www.cpdl.org/wiki/index.php/","Choral Public Domain Library page","991d7d60-01ee-41de-9b62-9ef3f86c2447","MusicBrainz"),
    ("BookBrainz","https://bookbrainz.org/creator/","BookBrainz page","f82f9342-a08d-46b7-ab7a-d8b6330c805d","MusicBrainz"),

    # Content
    ("Lyrics Page","https://","Page containing lyrics for the artist","e4d73442-3762-45a8-905c-401da65544ed","MusicBrainz"),
    ("Blog","https://","Artist blog","eb535226-f8ca-499d-9b18-6a144df4ae6f","MusicBrainz"),
    ("Biography","https://","Online biography of the artist","78f75830-94e1-4138-8f8a-643e3bb21ce5","MusicBrainz"),
    ("Discography Page","https://","Online discography of the artist's works","4fb0eeec-a6eb-4ae3-ad52-b55765b94e8f","MusicBrainz"),
    ("Interview","https://","URL containing an interview with the artist","1f171391-1f98-4f45-b191-038ec3b12395","MusicBrainz"),
    ("Image","https://","A pictorial image of the artist","221132e9-e30e-43f2-a741-15afc4c5fa7c","MusicBrainz"),
    ("Fan Page","https://","Fan-created website for the artist","f484f897-81cc-406e-96f9-cd799a04ee24","MusicBrainz"),
    ("Online Community","https://","Online community or forum for the artist","35b3a50f-bf0e-4309-a3b4-58eeed8cee6a","MusicBrainz"),
    ("Art Gallery","https://","Art gallery page e.g. DeviantArt, pixiv","8203341a-27be-40bb-b755-08d8ca9d7a9c","MusicBrainz"),

    # Funding / Tickets
    ("Crowdfunding","https://","Crowdfunding page e.g. Kickstarter, Indiegogo","93883cf6-e818-4938-990e-75863f8db2d3","MusicBrainz"),
    ("Patronage","https://","Patronage/donation page e.g. Patreon, PayPal.me","6f77d54e-1d81-4e1a-9ea5-37947577151b","MusicBrainz"),
    ("Ticketing","https://","Ticket purchase page for events","34beaf28-cbdd-4bf7-bc41-e7de18135245","MusicBrainz"),

    # Fallback
    ("Other","https://","External link that does not fit any other category",None,"Codervini"),
]
    for i in link_types:
            insert_multiple_columns_data(LinkTypeLookup,{"name":i[0],"base_url":i[1],"description":i[2],"alt_type_id":i[3],"ingestion_source":i[4]})
    logger.info(" Links Type Lookup Seeded")

def seed_work_type_lookup():
    work_types = [
    {"name": "Aria",            "description": "A self-contained piece for one voice usually with orchestral accompaniment. Most common inside operas, but also appear in cantatas, oratorios and concert arias."},
    {"name": "Audio drama",     "description": "A dramatized, purely acoustic performance, broadcast on radio or published on an audio medium (tape, CD, etc.)."},
    {"name": "Ballet",          "description": "Music composed to be used, together with a choreography, for a ballet dance production."},
    {"name": "Beijing opera",   "description": "A form of traditional Chinese theatre which combines music, vocal performance, mime, dance, and acrobatics."},
    {"name": "Cantata",         "description": "A vocal (often choral) composition with an instrumental (usually orchestral) accompaniment, typically in several movements."},
    {"name": "Concerto",        "description": "A musical work for soloist(s) accompanied by an orchestra."},
    {"name": "Étude",           "description": "An instrumental musical composition, usually of considerable difficulty, designed to provide practice material for perfecting a particular technical skill."},
    {"name": "Incidental music","description": "Music written as background for (usually) a theatre play."},
    {"name": "Madrigal",        "description": "A type of secular vocal music composition. In its original form, it had no instrumental accompaniment, although accompaniment is much more common in later madrigals."},
    {"name": "Mass",            "description": "A choral composition setting the invariable portions of the Christian Eucharistic liturgy (Kyrie - Gloria - Credo - Sanctus - Benedictus - Agnus Dei) to music."},
    {"name": "Motet",           "description": "A term that applies to different types of (usually unaccompanied) choral works. What exactly is a motet depends quite a bit on the period."},
    {"name": "Musical",         "description": "A form of theatrical performance that combines songs, spoken dialogue, acting, and dance."},
    {"name": "Opera",           "description": "A dramatised work (text + musical score) for singers and orchestra/ensemble. In true operas all dialog is sung, through arias and recitatives, but some styles of opera include spoken dialogue."},
    {"name": "Operetta",        "description": "A genre of light opera, in terms both of music and subject matter. Operettas are generally short and include spoken parts."},
    {"name": "Oratorio",        "description": "A large (usually sacred) musical composition including an orchestra, a choir, and soloists. Usually not performed theatrically (it lacks costumes, props and strong character interaction)."},
    {"name": "Overture",        "description": "Generally, the instrumental introduction to an opera. Independent ('concert') overtures also exist, which are generally programmatic works shorter than a symphonic poem."},
    {"name": "Partita",         "description": "An instrumental piece composed of a series of variations, very similar to a suite by its current definition."},
    {"name": "Play",            "description": "A form of literature usually consisting of scripted dialogue between characters, intended for theatrical performance rather than just reading."},
    {"name": "Poem",            "description": "A literary piece, generally short and in verse, where words are usually chosen for their sound and for the images and ideas they suggest."},
    {"name": "Prose",           "description": "Literary works written in prose — relatively ordinary language without metrical structure (e.g. novels, short stories, essays)."},
    {"name": "Quartet",         "description": "A musical composition scored for four voices or instruments."},
    {"name": "Song",            "description": "A composition for voice, with or without instruments, performed by singing. The most common form in folk and popular music, also fairly common in a classical context ('art songs')."},
    {"name": "Song-cycle",      "description": "A group of songs designed to be performed in a sequence as a single entity, usually by the same composer using words from the same poet or lyricist."},
    {"name": "Sonata",          "description": "A general term for small scale (very often solo or solo + keyboard) instrumental works, initially in baroque music."},
    {"name": "Soundtrack",      "description": "Music that accompanies a film, TV program, videogame, or even book."},
    {"name": "Suite",           "description": "An ordered set of instrumental or orchestral pieces normally performed in a concert setting. May be extracts from a ballet or opera, or entirely original movements."},
    {"name": "Symphonic poem",  "description": "A piece of programmatic orchestral music, usually in a single movement, that evokes a painting, landscape, poem, story or other non-musical source."},
    {"name": "Symphony",        "description": "An extended composition, almost always scored for orchestra without soloists."},
    {"name": "Zarzuela",        "description": "A Spanish lyric-dramatic work that alternates between spoken and sung scenes, incorporating operatic and popular song, as well as dance."},
    ]
    for i in work_types:
                insert_multiple_columns_data(WorkTypeLookup,{"name":i["name"],"description":i["description"]})
    logger.info(" Work Type Lookup Seeded")

def seed_iso_language_lookup():
    import pycountry
    import importlib.metadata

    version = importlib.metadata.version("pycountry")
    ingestion_source = f"pycountry v{version}: iso639-3"

    for lang in pycountry.languages:
        insert_multiple_columns_data(ISOLanguageLookup, {
            "name":             lang.name,
            "iso_639_1":        getattr(lang, "alpha_2",      None),
            "iso_639_2":        getattr(lang, "bibliographic", None) ,
            "iso_639_3":        lang.alpha_3,
            "is_active":        lang.type == "L",
            "ingestion_source": ingestion_source,
        })

    logger.info(" ISO Language Lookup Seeded")

def seed_artist_roles_lookup():
    ARTIST_ROLES = [
    # --- WORK ---
    ("writer",              "Wrote the music and/or words when more specific composer/lyricist credit is unavailable."),
    ("composer",            "Wrote the music (not necessarily the lyrics) for a work."),
    ("lyricist",            "Wrote the lyrics for a work."),
    ("librettist",          "Wrote the libretto for an opera, musical, or similar staged work."),
    ("translator",          "Translated the lyrics or libretto of a work into another language."),
    ("arranger",            "Arranged a composition into a form suitable for a specific ensemble or performance."),
    ("instrument_arranger", "Arranged the instrumental parts of a composition for performance."),
    ("vocal_arranger",      "Arranged the vocal parts of a composition for performance."),
    ("orchestrator",        "Adapted a composition for orchestra without substantially changing the musical substance."),
    ("revised_by",          "Revised a work, usually the original composer at a later date."),
    ("reconstructed_by",    "Reconstructed a work (usually one where the score was lost) to make it ready for performance."),
    ("adapter",             "Adapted a work from a different medium, e.g. prose into audio drama or stage musical into film."),
    ("scriptwriter",        "Wrote the original script for a dramatised work such as an audio drama."),
    ("choreographer",       "Created the choreography for a work, often a ballet."),
    ("commissioned",        "Commissioned the creation of a work."),

    # --- RECORDING ---
    ("performer",           "General performer credit on a recording when no instrument or vocal type is specified."),
    ("vocalist",            "Performed vocals on a recording."),
    ("instrumentalist",     "Performed one or more instruments on a recording."),
    ("conductor",           "Conducted an orchestra, band, or choir on a recording."),
    ("orchestra",           "An orchestra that performed on a recording."),
    ("chorus_master",       "Directed a choir that performed on a recording."),
    ("concertmaster",       "Led the orchestra or band as principal player on a recording."),
    ("audio_director",      "Responsible for the creative realisation of an audio project such as an audio drama or audiobook."),
    ("producer",            "Responsible for the creative and practical day-to-day aspects of making a recording."),
    ("mix_engineer",        "Mixed the recorded tracks into a final release-ready piece using a mixing console."),
    ("mastering_engineer",  "Mastered the audio for release. MB tracks this at release level."),
    ("recording_engineer",  "Captured the performance to tape or digital medium."),
    ("balance_engineer",    "Engineered the balance of sound levels during a recording or mixing session."),
    ("audio_engineer",      "Operated or maintained machines used to generate or modify sound in analogue or digital form."),
    ("sound_engineer",      "Ensured sounds reached microphones cleanly, without unwanted resonance or noise."),
    ("editor",              "Connected or redistributed recorded elements; may include producing radio edits."),
    ("field_recordist",     "Recorded field recordings for a recording or release."),
    ("programmer",          "Programmed electronic instruments such as synthesizers or drum machines."),
    ("remixer",             "Substantially altered and remixed one or more tracks into a new recording."),
    ("dj_mixer",            "DJ who mixed a continuous mix recording or release."),
    ("compiler",            "Selected and sequenced the tracks for a compilation."),
    ("sound_effects",       "Created or provided sound effects for a recording."),
    ("samples_from",        "Produced material that was sampled in another recording."),
    ("video_director",      "Directed the music video for a recording."),
    ("video_appearance",    "Appears in a music video without performing on the audio track."),
    ("cinematographer",     "Served as director of photography for a music video."),
    ("animator",            "Worked on animation for a music video."),
    ("instrument_technician","Maintained or tuned instruments for a recording or release; includes piano tuner credits."),
    ("creative_direction",  "Provided general creative inspiration during recording without contributing to writing or performance."),
    ("art_direction",       "Did the art direction for a recording or release."),
    ("artwork",             "Provided artwork for a recording or release."),
    ("design",              "Did visual design work for a recording or release."),
    ("graphic_design",      "Did graphic design or layout for a recording or release."),
    ("illustration",        "Did illustration work for a recording or release."),
    ("photography",         "Photographs included as part of a recording or release."),
    ("artists_and_repertoire", "Talent scouting, artistic development, and liaison between artists and labels."),
    ("phonographic_copyright", "Holds the phonographic copyright (℗) for a recording or release."),
    ("copyright_holder",    "Holds the general copyright (©) for a release."),
    ("publisher",           "Published the work or release. Distinct from the record label."),
    ("liner_notes",         "Authored the liner notes provided with a release."),
    ("booking",             "Responsible for booking the studio or venue where the recording was made."),
    ("legal_representation","Provided legal representation for a recording or release."),
    ("production_coordinator", "Coordinated the production of a release."),
    ("lacquer_cut",         "Cut the lacquer for a vinyl release."),
    ("transfer_engineer",   "Transferred a release from one medium to another, e.g. tape to digital."),
    ("booklet_editor",      "Edited the booklet accompanying a release."),
    ("misc",                "Miscellaneous role not covered by any other type."),

    # --- MCA-specific (no direct MB type) ---
    ("main_artist",         "Primary credited artist on a recording or release."),
    ("featured",            "Guest or featured artist credited on a recording."),
    ("cover_artist",        "Performs a cover version of another artist's original work."),
    ("original_performer",  "The artist who first recorded or performed a work.")
    ]
    for i in ARTIST_ROLES:
        insert_multiple_columns_data(ArtistRolesLookup,{"name":i[0],"description":i[1]})
    else:    
        logger.info(" Artist Roles Type Lookup Seeded")
    
def seed_credit_source_lookup():
    CREDIT_SOURCE_SEED = [
    # --- Core music metadata DBs ---
    ("musicbrainz",         "https://musicbrainz.org",              "Open community music encyclopedia with detailed credits and relationships."),
    ("discogs",             "https://www.discogs.com",              "Community-built database of physical and digital release credits and labels."),
    ("allmusic",            "https://www.allmusic.com",             "Professionally curated music database with credits, biographies and reviews."),
    ("gracenote",           "https://www.gracenote.com",            "Commercial music metadata and audio fingerprinting service used widely in consumer electronics."),
    ("theaudiodb",          "https://www.theaudiodb.com",           "Community music database with artist bios, artwork and social links."),
    ("jaxsta",              "https://jaxsta.com",                   "Official music credits database sourced from major labels and distributors. Went into hibernation Dec 2025."),
    ("secondhandsongs",     "https://secondhandsongs.com",          "User-generated database of cover versions and samples with work-level attribution."),
    ("whosampled",          "https://www.whosampled.com",           "Community database of samples, covers and remixes with source attribution."),
    ("rate_your_music",     "https://rateyourmusic.com",            "Community-rated music catalog with discography and release metadata."),
    ("sound_credit",        "https://soundcredit.com",              "Multimodal platform for entering and editing official music credits."),
    ("imvdb",               "https://imvdb.com",                    "Internet Music Video Database; tracks credits for music videos."),

    # --- Lyrics & annotations ---
    ("genius",              "https://genius.com",                   "Lyrics and song annotation platform with songwriter and producer credits."),
    ("musixmatch",          "https://www.musixmatch.com",           "Lyrics database and audio recognition platform with track metadata."),

    # --- Streaming platforms (carry metadata in their APIs) ---
    ("spotify",             "https://www.spotify.com",              "Streaming platform; provides track, artist and album metadata via Web API."),
    ("apple_music",         "https://music.apple.com",              "Apple Music / iTunes catalog metadata via the iTunes Search and MusicKit APIs."),
    ("deezer",              "https://www.deezer.com",               "Streaming platform providing track and artist metadata via public API."),
    ("tidal",               "https://tidal.com",                    "Hi-fi streaming platform with track and artist metadata including credits on some releases."),
    ("qobuz",               "https://www.qobuz.com",                "Hi-res streaming and download platform with detailed album and credits metadata."),
    ("amazon_music",        "https://music.amazon.com",             "Amazon Music streaming catalog with track and artist metadata."),
    ("youtube_music",       "https://music.youtube.com",            "YouTube Music catalog metadata accessible via YouTube Data API."),
    ("soundcloud",          "https://soundcloud.com",               "Audio platform with user-uploaded track and artist metadata via public API."),
    ("bandcamp",            "https://bandcamp.com",                 "Artist-direct platform with release and credit metadata on album pages."),
    ("beatport",            "https://www.beatport.com",             "Electronic music store and streaming platform with track and label metadata."),
    ("napster",             "https://www.napster.com",              "Music streaming platform with track and artist metadata via API."),

    # --- Fingerprinting & identification ---
    ("acoustid",            "https://acoustid.org",                 "Open-source audio fingerprinting service linked to MusicBrainz recordings."),
    ("acrcloud",            "https://www.acrcloud.com",             "Commercial audio fingerprinting and music recognition service."),
    ("shazam",              "https://www.shazam.com",               "Audio recognition service with track and artist metadata."),

    # --- Rights & royalty DBs ---
    ("the_mlc",             "https://www.themlc.com",               "US Mechanical Licensing Collective; authoritative database of musical works and recording-to-work mappings."),
    ("ascap",               "https://www.ascap.com",                "US PRO; Songview repertoire search with songwriter and publisher credits."),
    ("bmi",                 "https://www.bmi.com",                  "US PRO; repertoire database with songwriter and publisher credits."),
    ("sesac",               "https://www.sesac.com",                "US PRO; repertoire and licensing data for affiliated songwriters and publishers."),
    ("gmr",                 "https://www.globalmusicroyalties.com", "US PRO representing select major artists; part of Songview from Sep 2025."),
    ("socan",               "https://www.socan.com",                "Canadian PRO with public repertoire search for songwriter and publisher credits."),
    ("prs",                 "https://www.prsformusic.com",          "UK PRO; repertoire database with songwriter and publisher credits."),
    ("sacem",               "https://www.sacem.fr",                 "French PRO; repertoire database with songwriter and publisher credits."),
    ("cisac",               "https://www.cisac.org",                "Global confederation of authors and composers societies; governs ISWC and IPI standards."),
    ("isni",                "https://www.isni.org",                 "International Standard Name Identifier; authoritative IDs for creative contributors."),
    ("wikidata",            "https://www.wikidata.org",             "Structured knowledge base providing artist identifiers and external links via SPARQL."),

    # --- Structured identifier sources ---
    ("credits_fm",          "https://credits.fm",                   "Open CC-BY database cross-verifying ISRC, ISWC, IPI, ISNI and UPC across MLC, MusicBrainz, CISAC and streaming platforms."),

    # --- Genre-specific DBs ---
    ("encyclopaedia_metallum", "https://www.metal-archives.com",    "Comprehensive heavy metal encyclopedia with band and release credits."),
    ("vgmdb",               "https://vgmdb.net",                    "Database for video game, anime and doujin music soundtracks with detailed credits."),

    # --- General knowledge ---
    ("wikipedia",           "https://www.wikipedia.org",            "General encyclopaedia used as supplementary artist biography and context source."),

    # --- File-level / local sources ---
    ("embedded_tags",       None,                                   "Credit extracted from embedded audio file tags (ID3, Vorbis comment, APEv2, etc.) at import time."),
    ("filename",            None,                                   "Credit inferred from the audio file name at import time."),
    ("liner_notes",         None,                                   "Credit manually extracted from physical or digital release liner notes or booklets."),
    ("user_manual",         None,                                   "Credit entered or corrected manually by the user."),
    ("unknown",             None,                                   "Credit source is not known or was not recorded at ingestion time."),
    ]
    for i in CREDIT_SOURCE_SEED:
            insert_multiple_columns_data(CreditSourceLookup,{"name":i[0],"source_url":i[1],"description":i[2]})
    else:    
        logger.info(" Credit Source Lookup Seeded")
        


    
def seed_all_lookup():
    seed_credit_source_lookup()
    seed_artist_roles_lookup()
    seed_work_type_lookup()
    seed_iso_language_lookup()
    seed_link_types_lookup()
    seed_artist_type_lookup()
    seed_alias_types_lookup()
    seed_locale_lookup()
    seed_gender_lookup()
    seed_country_lookup_restcountries()

seed_all_lookup()
