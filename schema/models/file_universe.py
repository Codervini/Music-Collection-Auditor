import dotenv
from mca_tools.machine_identifier import machine_id
from mca_tools.enums import *
from sqlalchemy import (
    Column, Text, Boolean, SmallInteger, Integer, Date,
    String, TIMESTAMP, Index, text, Enum,
    UniqueConstraint, ForeignKey, create_engine ,ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from schema.base import Base, DB_ENGINE

"""
music_library/schema.py
=======================
Song Library Module — Core Database Schema
Groups: Artists, Works, Recordings, Releases, Tracks,
        Physical Files, File Quality Profile, Tags

Table Hierarchy (read bottom up for authority):
    physical_files      →  recordings  →  works  (the truth)
    file_quality_profile→  physical_files         (quality metadata, TBD computation)
    tracks              →  recordings  +  releases
    *_credits           →  artists    (who did what)
    tags                →  anything   (flexible labelling)

NOTE: All tables carry:
    - id         UUID v7  PK NN IDX
    - mca_pid    VARCHAR(1024) NN
    - created_at TIMESTAMPTZ NN
    - updated_at TIMESTAMPTZ NN
    - updated_by UUID FK → machines.id (nullable — machines universe TBD)
"""


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — ARTISTS
# ══════════════════════════════════════════════════════════════════════════════

class Artists(Base):
    """
    Every person or group who ever touched a song in this library.
    One row per unique artist — never duplicated.
    Referenced by work_credits, recording_credits, release_credits.
    """
    __tablename__ = "artists"

    id               = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid          = Column(String(1024), nullable=True)
    name             = Column(Text, nullable=False,unique=False)                         # display name e.g. "Freddie Mercury"
    sort_name        = Column(Text, nullable=True)                          # sortable e.g. "Mercury, Freddie"
    type_id          = Column(SmallInteger, ForeignKey("artist_type_lookup.id"), nullable=True)
    gender_id        = Column(SmallInteger, ForeignKey("gender_lookup.id"), nullable=True)
    mbid             = Column(String(36), nullable=True, unique=True)                    # MusicBrainz artist ID
    isni             = Column(String(16), nullable=True)                    # International Standard Name Identifier
    country_id       = Column(SmallInteger, ForeignKey("country_lookup.id"), nullable=True)  # replaces raw country string
    born_or_formed   = Column(Date, nullable=True)
    died_or_disbanded= Column(Date, nullable=True)
    disambiguation   = Column(Text, nullable=True)                          # e.g. "Queen guitarist" if name clash
    data_complete    = Column(Boolean, default=False , nullable=False)
    raw_mb_response  = Column(JSONB, nullable=True)                         # full MusicBrainz API response
    created_at       = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at       = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by       = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_artists_name",      "name"),
        Index("ix_artists_sort_name", "sort_name"),
        Index("ix_artists_type_id",   "type_id"),
        Index("ix_artists_country_id","country_id"),
    )


class ArtistAliases(Base):
    """
    Alternative names for an artist.
    One row per alias. An artist can have many aliases.
    e.g. "The Weeknd" has legal name "Abel Tesfaye"
    """
    __tablename__ = "artist_aliases"

    id              = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid         = Column(String(1024), nullable=True)
    artist_id       = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    alias_type_id   = Column(SmallInteger, ForeignKey("alias_types_lookup.id"), nullable=True)
    name            = Column(Text, nullable=False)                          # the alias
    sort_name       = Column(Text, nullable=True)
    locale_id       = Column(SmallInteger, ForeignKey("locale_lookup.id"), nullable=True)   # replaces raw locale string
    is_primary      = Column(Boolean, nullable=True)
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by      = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_artist_aliases_artist_id", "artist_id"),
        Index("ix_artist_aliases_name",      "name"),
        Index("ix_artist_aliases_locale_id", "locale_id"),
    )


class ArtistLinks(Base):
    """
    External URLs for an artist — Spotify, Wikipedia, Instagram etc.
    One row per link per artist.
    """
    __tablename__ = "artist_links"

    id              = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid         = Column(String(1024), nullable=True)
    artist_id       = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    link_type_id    = Column(SmallInteger, ForeignKey("link_types_lookup.id"), nullable=False)
    url             = Column(Text, nullable=False)
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by      = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("artist_id", "link_type_id", name="uq_artist_links_artist_type"),
        Index("ix_artist_links_artist_id",    "artist_id"),
        Index("ix_artist_links_link_type_id", "link_type_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 3 — WORKS
# A work is the song as a pure concept.
# ══════════════════════════════════════════════════════════════════════════════

class Works(Base):
    """
    The song concept. Pure idea, no audio.
    One row per unique song concept.
    All recordings of this song point back here.
    """
    __tablename__ = "works"

    id              = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid         = Column(String(1024), nullable=True)
    title           = Column(Text, nullable=False)                          # song name
    type_id         = Column(SmallInteger, ForeignKey("work_type_lookup.id"), nullable=True)
    iswc = Column(ARRAY(String(15)), nullable=True)                     # International Standard Musical Work Code
    language_id     = Column(SmallInteger, ForeignKey("iso_language_lookup.id"), nullable=True)  # replaces raw language string
    mbid            = Column(String(36), nullable=True)                     # MusicBrainz work ID
    disambiguation  = Column(Text, nullable=True)    
    raw_mb_response = Column(JSONB, nullable=True)
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by      = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_works_mbid",        "mbid"),
        Index("ix_works_title",       "title"),
        Index("ix_works_iswc",        "iswc"),
        Index("ix_works_type_id",     "type_id"),
        Index("ix_works_language_id", "language_id"),
    )


class WorkCredits(Base):
    """
    Who was involved in creating this work concept.
    Composer, lyricist, original performer.
    One row per artist per role per work.
    """
    __tablename__ = "work_credits"

    id                  = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid             = Column(String(1024), nullable=True)
    work_id             = Column(UUID(as_uuid=True), ForeignKey("works.id"), nullable=False)
    artist_id           = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    role_id             = Column(SmallInteger, ForeignKey("artist_roles_lookup.id"), nullable=True)
    credit_source_id    = Column(SmallInteger, ForeignKey("credit_source_lookup.id"), nullable=True)
    credit_source_url   = Column(Text, nullable=True)                     
    note                = Column(Text, nullable=True)
    created_at          = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at          = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by          = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("work_id", "artist_id", "role_id", name="uq_work_credits"),
        Index("ix_work_credits_work_id",          "work_id"),
        Index("ix_work_credits_artist_id",        "artist_id"),
        Index("ix_work_credits_role_id",          "role_id"),
        Index("ix_work_credits_credit_source_id", "credit_source_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 4 — RECORDINGS
# A recording is a specific captured version of a work.
# THE TRUTH. Everything else orbits this.
# ══════════════════════════════════════════════════════════════════════════════

class Recordings(Base):
    """
    Every specific version of a work ever captured.
    Studio 1975, Live Aid 1985, 2011 Remaster — three separate rows.

    Title columns:
        official_title   — the canonical release title as credited officially
        version_name     — nullable human label for the version, e.g. "Live Aid 1985"
        title            — full display title, e.g. "Bohemian Rhapsody (Live Aid 1985)"
    """
    __tablename__ = "recordings"

    id                   = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid              = Column(String(1024), nullable=True)
    work_id              = Column(UUID(as_uuid=True), ForeignKey("works.id"), nullable=False)
    version_type_id      = Column(SmallInteger, ForeignKey("version_type_lookup.id"), nullable=False)
    official_title       = Column(Text, nullable=False)                     # canonical credited title
    version_name         = Column(Text, nullable=True)                      # e.g. "Live Aid 1985", "2011 Remaster"
    title                = Column(Text, nullable=False)                     # full display title incl version
    duration_ms          = Column(Integer, nullable=True)
    acoustid_fingerprint = Column(Text, nullable=True)
    acoustid_mbid        = Column(String(36), nullable=True)
    mb_recording_id      = Column(String(36), nullable=True)                # MusicBrainz recording ID
    isrc                 = Column(String(12), nullable=True)
    language_id          = Column(SmallInteger, ForeignKey("iso_language_lookup.id"), nullable=True)
    raw_mb_response      = Column(JSONB, nullable=True)
    created_at           = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at           = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by           = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_recordings_work_id",              "work_id"),
        Index("ix_recordings_mb_recording_id",      "mb_recording_id"),
        Index("ix_recordings_isrc",                 "isrc"),
        Index("ix_recordings_acoustid_fingerprint", "acoustid_fingerprint"),
        Index("ix_recordings_acoustid_mbid",        "acoustid_mbid"),
        Index("ix_recordings_version_type_id",      "version_type_id"),
        Index("ix_recordings_language_id",          "language_id"),
        Index("ix_recordings_official_title",       "official_title"),
    )


class RecordingCredits(Base):
    """
    Who was involved in this specific recording.
    Main artist, featured artist, producer, remixer, conductor.
    One row per artist per role per recording.
    """
    __tablename__ = "recording_credits"

    id                  = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid             = Column(String(1024), nullable=False)
    recording_id        = Column(UUID(as_uuid=True), ForeignKey("recordings.id"), nullable=False)
    artist_id           = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    role_id             = Column(SmallInteger, ForeignKey("artist_roles_lookup.id"), nullable=False)
    credit_source_id    = Column(SmallInteger, ForeignKey("credit_source_lookup.id"), nullable=True)
    credit_source_url   = Column(Text, nullable=True)
    credit_order        = Column(SmallInteger, nullable=True)
    note                = Column(Text, nullable=True)
    created_at          = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at          = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by          = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("recording_id", "artist_id", "role_id", name="uq_recording_credits"),
        Index("ix_recording_credits_recording_id",      "recording_id"),
        Index("ix_recording_credits_artist_id",         "artist_id"),
        Index("ix_recording_credits_role_id",           "role_id"),
        Index("ix_recording_credits_credit_source_id",  "credit_source_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 5 — RELEASES
# ══════════════════════════════════════════════════════════════════════════════

class Releases(Base):
    """
    Every album, single, or EP ever released that contains
    a recording in this library.
    One row per release product.
    """
    __tablename__ = "releases"

    id              = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid         = Column(String(1024), nullable=True)
    title           = Column(Text, nullable=False)
    type_id         = Column(SmallInteger, ForeignKey("release_type_lookup.id"), nullable=True)
    year            = Column(SmallInteger, nullable=True)
    date            = Column(Date, nullable=True)
    label           = Column(Text, nullable=True)
    country_id      = Column(SmallInteger, ForeignKey("country_lookup.id"), nullable=True)    # replaces raw country string
    barcode         = Column(String(32), nullable=True)
    mb_release_id   = Column(String(36), nullable=True)
    artwork_url     = Column(Text, nullable=True)
    artwork_local   = Column(Text, nullable=True)
    total_tracks    = Column(SmallInteger, nullable=True)
    total_discs     = Column(SmallInteger, nullable=True)
    raw_mb_response = Column(JSONB, nullable=True)
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by      = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_releases_mb_release_id",       "mb_release_id"),
        Index("ix_releases_title",      "title"),
        Index("ix_releases_year",       "year"),
        Index("ix_releases_type_id",    "type_id"),
        Index("ix_releases_barcode",    "barcode"),
        Index("ix_releases_country_id", "country_id"),
    )


class ReleaseCredits(Base):
    """
    Who is credited on this release.
    Main artist, featured artist, various artists for compilations.
    One row per artist per role per release.
    """
    __tablename__ = "release_credits"

    id                  = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid             = Column(String(1024), nullable=False)
    release_id          = Column(UUID(as_uuid=True), ForeignKey("releases.id"), nullable=False)
    artist_id           = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    role_id             = Column(SmallInteger, ForeignKey("artist_roles_lookup.id"), nullable=False)
    credit_source_id    = Column(SmallInteger, ForeignKey("credit_source_lookup.id"), nullable=True)
    credit_source_url   = Column(Text, nullable=True)
    credit_order        = Column(SmallInteger, nullable=False, server_default=text("1"))
    note                = Column(Text, nullable=True)
    created_at          = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at          = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by          = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("release_id", "artist_id", "role_id", name="uq_release_credits"),
        Index("ix_release_credits_release_id",          "release_id"),
        Index("ix_release_credits_artist_id",           "artist_id"),
        Index("ix_release_credits_role_id",             "role_id"),
        Index("ix_release_credits_credit_source_id",    "credit_source_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — TRACKS
# The bridge between recordings and releases.
# ══════════════════════════════════════════════════════════════════════════════

class Tracks(Base):
    """
    Links a recording to a release with a position number.
    One recording can appear on many releases — one track row each time.
    mb_track_id: MusicBrainz track ID (distinct from recording MBID).
    """
    __tablename__ = "tracks"

    id           = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid      = Column(String(1024), nullable=False)
    recording_id = Column(UUID(as_uuid=True), ForeignKey("recordings.id"), nullable=False)
    release_id   = Column(UUID(as_uuid=True), ForeignKey("releases.id"), nullable=False)
    position     = Column(SmallInteger, nullable=False)
    disc_number  = Column(SmallInteger, nullable=False, server_default=text("1"))
    title        = Column(Text, nullable=True)                              # if different from recording title
    duration_ms  = Column(Integer, nullable=True)                           # if different from recording
    mb_track_id  = Column(String(36), nullable=True)                        # MusicBrainz track ID
    created_at   = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at   = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by   = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("recording_id", "release_id", name="uq_tracks_recording_release"),
        UniqueConstraint("release_id", "disc_number", "position", name="uq_tracks_position"),
        Index("ix_tracks_recording_id", "recording_id"),
        Index("ix_tracks_release_id",   "release_id"),
        Index("ix_tracks_mb_track_id",         "mb_track_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 7 — PHYSICAL FILES
# The files you actually have on your disk.
# ══════════════════════════════════════════════════════════════════════════════

class PhysicalFiles(Base):
    """
    Your actual audio files on disk.
    Multiple formats of the same recording all point to the same recording_id.
    This is YOUR data — everything above comes from MusicBrainz.

    Extended file info columns capture everything the audio container exposes:
    embedded tags, codec details, replay gain, and stream properties.
    """
    __tablename__ = "physical_files"

    id                   = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid              = Column(String(1024), nullable=False)

    # Core identity
    recording_id         = Column(UUID(as_uuid=True), ForeignKey("recordings.id"), nullable=False)
    format_id            = Column(SmallInteger, ForeignKey("file_format_lookup.id"), nullable=False)

    # File system
    file_path            = Column(Text, nullable=False)                     # full path on disk
    file_hash            = Column(String(64), nullable=False)               # SHA-256 whole file
    audio_hash           = Column(String(64), nullable=True)                # SHA-256 audio stream only
    file_size_bytes      = Column(Integer, nullable=True)

    # Audio stream properties
    bitrate              = Column(Integer, nullable=True)                   # kbps
    bitrate_mode         = Column(String(8), nullable=True)                 # CBR | VBR | ABR
    sample_rate          = Column(Integer, nullable=True)                   # Hz
    bit_depth            = Column(SmallInteger, nullable=True)              # 16 | 24 | 32
    channels             = Column(SmallInteger, nullable=True)              # 1=mono, 2=stereo, 6=5.1
    duration_ms          = Column(Integer, nullable=True)

    # Embedded tag snapshot (raw values read from the file at ingestion)
    embedded_title       = Column(Text, nullable=True)
    embedded_artist      = Column(Text, nullable=True)
    embedded_album       = Column(Text, nullable=True)
    embedded_track_num   = Column(SmallInteger, nullable=True)
    embedded_disc_num    = Column(SmallInteger, nullable=True)
    embedded_year        = Column(String(8), nullable=True)                 # raw string as stored in tag
    embedded_genre       = Column(Text, nullable=True)
    embedded_isrc        = Column(String(12), nullable=True)
    embedded_mbid        = Column(String(36), nullable=True)                # MBID embedded in file tags
    embedded_label       = Column(Text, nullable=True)
    has_embedded_artwork = Column(Boolean, nullable=True)

    # Replay gain
    replay_gain_track    = Column(Text, nullable=True)                      # e.g. "-6.54 dB"
    replay_gain_album    = Column(Text, nullable=True)

    added_at             = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at           = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by           = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_physical_files_recording_id",  "recording_id"),
        Index("ix_physical_files_file_hash",     "file_hash"),
        Index("ix_physical_files_audio_hash",    "audio_hash"),
        Index("ix_physical_files_format_id",     "format_id"),
        Index("ix_physical_files_embedded_mbid", "embedded_mbid"),
        Index(
            "ix_physical_files_duplicates",
            "audio_hash",
            postgresql_where=text("audio_hash IS NOT NULL")
        ),
    )


class FileQualityProfile(Base):
    """
    One-to-one with physical_files.
    Placeholder table for computed quality metadata.
    Computation logic TBD — this table holds space for future occupation.

    quality_label:  exact human string e.g. "FLAC 96kHz/24bit", "MP3 320kbps CBR"
    quality_tier_id: FK to quality_tier_lookup for filtering e.g. Hi-Res, Lossless, High Quality
    computed_at:    when the quality profile was last computed
    """
    __tablename__ = "file_quality_profile"

    id               = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid          = Column(String(1024), nullable=False)
    physical_file_id = Column(UUID(as_uuid=True), ForeignKey("physical_files.id"), nullable=False, unique=True)
    quality_tier_id  = Column(SmallInteger, ForeignKey("quality_tier_lookup.id"), nullable=True)
    quality_label    = Column(String(128), nullable=True)                   # e.g. "FLAC 96kHz/24bit"
    computed_at      = Column(TIMESTAMP(timezone=True), nullable=True)      # null = not yet computed
    created_at       = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at       = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by       = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_file_quality_profile_physical_file_id", "physical_file_id"),
        Index("ix_file_quality_profile_quality_tier_id",  "quality_tier_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 8 — TAGS
# Flexible labelling system for any entity.
# ══════════════════════════════════════════════════════════════════════════════

class Tags(Base):
    """
    A tag can attach to any entity — work, recording, release, artist.
    entity_type_id tells you which table entity_id refers to.
    source_id tells you where the tag came from — MusicBrainz, user, Last.fm etc.
    tag_id is now a FK to tag_lookup — replaces the old free-text tag column.
    """
    __tablename__ = "tags"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    mca_pid        = Column(String(1024), nullable=False)
    entity_type_id = Column(SmallInteger, ForeignKey("entity_type_lookup.id"), nullable=False)
    entity_id      = Column(UUID(as_uuid=True), nullable=False)             # points to whichever table
    tag_id         = Column(SmallInteger, ForeignKey("tag_lookup.id"), nullable=False)   # replaces free-text tag
    source_id      = Column(SmallInteger, ForeignKey("tag_source_lookup.id"), nullable=False)
    created_at     = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at     = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by     = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("entity_type_id", "entity_id", "tag_id", "source_id", name="uq_tags"),
        Index("ix_tags_entity_id",      "entity_id"),
        Index("ix_tags_entity_type_id", "entity_type_id"),
        Index("ix_tags_tag_id",         "tag_id"),
        Index("ix_tags_source_id",      "source_id"),
    )


# Base.metadata.create_all(DB_ENGINE)