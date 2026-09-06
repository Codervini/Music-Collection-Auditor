from sqlalchemy import (
    Column, Text, Boolean, SmallInteger, Integer, Date,
    String, TIMESTAMP, Index, text, Enum,
    UniqueConstraint, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from schema.base import Base , DB_ENGINE
from schema.models.machines import *
"""
music_library/lookup_schema.py
==============================
Song Library Module — Lookup Tables
All reference/dictionary tables live here.

NOTE: machines table is defined in a separate universe (TBD).
      updated_by columns carry a FK stub — wire up when machines table is finalised.
"""


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — LOOKUP TABLES
# These are the "dictionaries" of the system.
# Every table that would have had an ENUM column
# now references one of these instead.
# Adding a new value = INSERT one row, no schema migration needed.
# ══════════════════════════════════════════════════════════════════════════════


class ArtistTypeLookup(Base):
    """
    What kind of entity an artist is.
    person, group, orchestra, choir, character
    """
    __tablename__ = "artist_type_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    alt_type_id = Column(UUID(True),nullable=True, unique=True)
    mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    ingestion_source = Column(String(256), nullable=False)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)   # FK → machines (TBD universe)


class GenderLookup(Base):
    """
    Gender of a person artist or group composition.
    male, female, non_binary, not_applicable,
    boygroup, girlgroup, mixed_group
    """
    __tablename__ = "gender_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class WorkTypeLookup(Base):
    """
    What kind of musical work this is.
    song, aria, symphony, soundtrack, jingle, poem, spoken_word
    """
    __tablename__ = "work_type_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
   # alt_type_id = Column(UUID(True), nullable=True, unique=True)
    # mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
   # ingestion_source = Column(String(256), nullable=False)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class VersionTypeLookup(Base):
    """
    What kind of recording version this is.
    original, live, remix, remaster, cover, acoustic,
    instrumental, medley, demo, radio_edit, extended
    """
    __tablename__ = "version_type_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class ReleaseTypeLookup(Base):
    """
    What kind of release product this is.
    album, single, ep, compilation, soundtrack,
    live_album, remix_album, mixtape, bootleg, other
    """
    __tablename__ = "release_type_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class FileFormatLookup(Base):
    """
    THE FILE FORMAT BIBLE.
    One row per audio codec/container combination.
    Describes the format itself — not any individual file.

    Formats: mp3, flac, opus, ogg, wav, aac, m4a, wma, ape, dsf, dff, aiff

    Bitrate guidance columns are informational / reference only.
    Actual per-file bitrate lives on physical_files.bitrate.
    """
    __tablename__ = "file_format_lookup"

    id                  = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid             = Column(String(256), nullable=True)

    # Identity
    name                = Column(String(16), nullable=False, unique=True)   # e.g. mp3, flac, opus
    full_name           = Column(String(128), nullable=True)                # e.g. "MPEG-1 Audio Layer III"
    container_format    = Column(String(32), nullable=True)                 # e.g. ID3, Ogg, MP4
    codec               = Column(String(64), nullable=True)                 # e.g. LAME, libopus, libFLAC
    file_extension      = Column(String(8), nullable=True)                  # e.g. .mp3, .flac
    mime_type           = Column(String(64), nullable=True)                 # e.g. audio/mpeg, audio/flac

    # Compression
    is_lossless         = Column(Boolean, nullable=False, server_default=text("false"))
    compression_type    = Column(String(32), nullable=True)                 # lossy | lossless | uncompressed
    supports_vbr        = Column(Boolean, nullable=True)                    # variable bitrate supported?
    supports_cbr        = Column(Boolean, nullable=True)                    # constant bitrate supported?

    # Bitrate reference (informational only — actual bitrate is on physical_files)
    min_bitrate_kbps    = Column(Integer, nullable=True)                    # lowest valid bitrate (kbps)
    max_bitrate_kbps    = Column(Integer, nullable=True)                    # highest valid bitrate (kbps)
    typical_bitrate_kbps= Column(Integer, nullable=True)                   # most common/recommended (kbps)

    # Sample rate / depth
    max_sample_rate_hz  = Column(Integer, nullable=True)                    # e.g. 192000 for Hi-Res
    max_bit_depth       = Column(SmallInteger, nullable=True)               # e.g. 16, 24, 32

    # Metadata & tagging
    supports_tags       = Column(Boolean, nullable=True)                    # embeds metadata tags?
    supports_artwork    = Column(Boolean, nullable=True)                    # embeds album art?
    tag_format          = Column(String(32), nullable=True)                 # ID3v2, Vorbis Comment, APEv2

    # General
    description         = Column(Text, nullable=True)                       # human notes on this format
    typical_use_case    = Column(Text, nullable=True)                       # e.g. "streaming", "archival"
    open_standard       = Column(Boolean, nullable=True)                    # is the codec open/royalty-free?

    created_at          = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at          = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by          = Column(String(64), ForeignKey("machines.id"), nullable=True)


class QualityTierLookup(Base):
    """
    Human-readable quality tier for a physical file.
    Assigned by computation logic (TBD) based on
    bitrate, sample_rate, bit_depth, and is_lossless.

    Examples:
        low_quality     → lossy, < 128 kbps
        standard        → lossy, 128–256 kbps
        high_quality    → lossy, 256–320 kbps
        lossless        → lossless, 44.1kHz/16bit (CD quality)
        hi_res          → lossless, > 44.1kHz or > 16bit
    """
    __tablename__ = "quality_tier_lookup"

    id              = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid         = Column(String(256), nullable=True)
    name            = Column(String(64), nullable=False, unique=True)       # e.g. hi_res, lossless
    label           = Column(String(64), nullable=False)                    # e.g. "Hi-Res", "Lossless (CD)"
    description     = Column(Text, nullable=True)
    tier_order      = Column(SmallInteger, nullable=False)                  # 1 = lowest, ascending quality
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by      = Column(String(64), ForeignKey("machines.id"), nullable=True)


class TagSourceLookup(Base):
    """
    Where a tag came from.
    musicbrainz, user, acoustid, lastfm, discogs
    """
    __tablename__ = "tag_source_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class TagLookup(Base):
    """
    Controlled vocabulary of tags used across the library.
    Replaces the previous free-text tag column on the tags table.
    One row per unique tag value.

    e.g. rock, 80s, guitar-driven, melancholic, workout
    source_id indicates where this tag definition originated.
    """
    __tablename__ = "tag_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)           # the tag e.g. "rock"
    description = Column(Text, nullable=True)
    source_id   = Column(SmallInteger, ForeignKey("tag_source_lookup.id"), nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_tag_lookup_name",      "name"),
        Index("ix_tag_lookup_source_id", "source_id"),
    )


class EntityTypeLookup(Base):
    """
    Which table a tag or link points to.
    work, recording, release, artist
    """
    __tablename__ = "entity_type_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    table_name  = Column(String(64), nullable=False)                        # actual db table name
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class AliasTypeLookup(Base):
    """
    What kind of alias an artist name is.
    artist_name, legal_name, search_hint, performance_name, abbreviation
    """
    __tablename__ = "alias_types_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class LinkTypeLookup(Base):
    """
    External platform or URL type for an artist.
    spotify, wikipedia, discogs, wikidata, youtube,
    instagram, official_site, soundcloud, bandcamp,
    lastfm, allmusic, twitter, facebook, tiktok
    """
    __tablename__ = "link_types_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    alt_type_id = Column(UUID(True), nullable=True, unique=True)
    #mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    base_url    = Column(Text, nullable=True)                               # e.g. https://open.spotify.com/artist/
    ingestion_source = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class ArtistRolesLookup(Base):
    """
    Every possible role an artist can have on a work, recording, or release.
    composer, lyricist, main_artist, featured, producer,
    remixer, arranger, conductor, orchestra, cover_artist,
    original_performer, mix_engineer, mastering_engineer
    """
    __tablename__ = "artist_roles_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
    #mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class CreditSourceLookup(Base):
    """
    Where a credit attribution came from.
    musicbrainz, discogs, user_manual, lastfm, allmusic, liner_notes
    Applies to work_credits, recording_credits, release_credits.
    """
    __tablename__ = "credit_source_lookup"

    id          = Column(SmallInteger, primary_key=True, autoincrement=True)
   # mca_pid     = Column(String(1024), nullable=True)
    name        = Column(String(64), nullable=False, unique=True)
    source_url  = Column(Text, nullable=True)                               # base URL of the source platform
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(String(64), ForeignKey("machines.id"), nullable=True)


class CountryLookup(Base):
    """
    ISO 3166-1 country reference table.
    Covers all sovereign states and territories.
    alpha2: 2-letter code (e.g. GB, US, IN)
    alpha3: 3-letter code (e.g. GBR, USA, IND)
    numeric: UN numeric code (e.g. 826, 840, 356)
    continent: Africa | Antarctica | Asia | Europe |
               North America | Oceania | South America
    """
    __tablename__ = "country_lookup"

    id              = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid         = Column(String(1024), nullable=True)
    name            = Column(String(128), nullable=False, unique=True)      # full country name
    official_name   = Column(String(512), nullable=False, unique=True) 
    alpha2          = Column(String(2), nullable=False, unique=True)        # ISO 3166-1 alpha-2
    alpha3          = Column(String(3), nullable=True, unique=True)         # ISO 3166-1 alpha-3
    numeric_code    = Column(String(3), nullable=True)                      # ISO numeric code
    continent       = Column(String(32), nullable=True)                     # continent name
    is_active       = Column(Boolean, nullable=False, server_default=text("true"))  # false = dissolved/historical
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by      = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_country_lookup_alpha2", "alpha2"),
        Index("ix_country_lookup_alpha3", "alpha3"),
    )


class LocaleLookup(Base):
    """
    IETF BCP 47 locale reference table.
    Combines language + optional region/script.
    e.g. en_US, en_GB, fr_FR, zh_Hans, pt_BR

    language_code: ISO 639-1 two-letter language code
    region_code:   ISO 3166-1 alpha-2 region (optional)
    script_code:   ISO 15924 script code (optional, e.g. Hans, Latn)
    """
    __tablename__ = "locale_lookup"

    id              = Column(SmallInteger, primary_key=True, autoincrement=True)
    mca_pid         = Column(String(1024), nullable=True)
    code            = Column(String(16), nullable=False, unique=True)       # full locale e.g. en_US
    language_code   = Column(String(8), nullable=False)                     # ISO 639-1 e.g. en
    region_code     = Column(String(4), nullable=True)                      # ISO 3166-1 alpha-2 e.g. US
    script_code     = Column(String(8), nullable=True)                      # ISO 15924 e.g. Hans
    display_name    = Column(String(128), nullable=True)                    # e.g. "English (United States)"
    is_rtl          = Column(Boolean, nullable=False, server_default=text("false"))  # right-to-left script?
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by      = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_locale_lookup_code",          "code"),
        Index("ix_locale_lookup_language_code", "language_code"),
    )


class ISOLanguageLookup(Base):
    """
    ISO 639 language reference table.
    iso_639_1:  2-letter code (e.g. en, fr, ja) — most common
    iso_639_2:  3-letter bibliographic code (e.g. eng, fra, jpn)
    iso_639_3:  3-letter individual language code (most granular)
    Used on works, recordings for language tagging.
    """
    __tablename__ = "iso_language_lookup"

    id              = Column(SmallInteger, primary_key=True, autoincrement=True)
    #mca_pid         = Column(String(1024), nullable=True)
    name            = Column(String(128), nullable=False, unique=True)   # English name of language
    iso_639_1       = Column(String(2), nullable=True, unique=True)      # 2-letter codes for major languages (may be null for rare langs)
    iso_639_2       = Column(String(3), nullable=True)                   # Legacy 3-letter, two variants — bibliographic (B-code) and terminological (T-code). 
                                                                         # Most languages have the same code for both. Set only when B differs.

    iso_639_3       = Column(String(3), nullable=False)                  # 3-letter code, covers all
    is_active       = Column(Boolean, nullable=False)
    ingestion_source = Column(String(256), nullable=False)
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by      = Column(String(64), ForeignKey("machines.id"), nullable=True)

    __table_args__ = (
        Index("ix_iso_language_lookup_iso_639_1", "iso_639_1"),
        Index("ix_iso_language_lookup_iso_639_2", "iso_639_2"),
    )

# Base.metadata.drop_all(DB_ENGINE,[CountryLookup.__table__])
# Base.metadata.create_all(DB_ENGINE,[CountryLookup.__table__])