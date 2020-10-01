#!/usr/bin/env python3

import sqlite3
import os
import sys
import time


# Config.
MUSIC_ROOT_DIR = '/media/droppie/libraries/music'
# MUSIC_ROOT_DIR = 'E:\\Music-Beets'
# BEETS_DB_FILEPATH = '/home/bart/music_library.db'
BEETS_DB_FILEPATH = '/media/droppie/libraries/music/.config/beets/library.db'
MPD_DB_FORMAT = 2
TAGCACHE_FILEPATH = '/home/bart/tag_cache'
GENRE_DELIMITER = ', '
MPD_VERSION = '0.21.19'


if __name__ == '__main__':
    starttime = time.time()

    fs_charset = sys.getfilesystemencoding().upper()

    # Windows paths or UNIX paths.
    if MUSIC_ROOT_DIR[0] == '/':
        import posixpath as ospath
    else:
        import ntpath as ospath

    # Database connection.
    db_connection = sqlite3.connect(BEETS_DB_FILEPATH)
    cursor = db_connection.cursor()

    # Tagcache file initialisation.
    tagcache_filehandle = open(TAGCACHE_FILEPATH, 'w')

    # Query the Beets database for all items.
    cursor.execute('''
        select
            items.path,
            items.length,
            items.artist,
            items.album,
            albums.albumartist,
            items.title,
            items.track,
            albums.genre,
            albums.year,
            items.disc,
            items.composer,
            items.arranger
        from items

        left join albums
        on items.album_id = albums.id

        order by items.path, items.track
    ''')

    # Write tag_cache header.
    tagcache_filehandle.write(f'''\
info_begin
format: {MPD_DB_FORMAT}
mpd_version: {MPD_VERSION}
fs_charset: {fs_charset}
tag: Artist
tag: ArtistSort
tag: Album
tag: AlbumSort
tag: AlbumArtist
tag: AlbumArtistSort
tag: Title
tag: Track
tag: Name
tag: Genre
tag: Date
tag: OriginalDate
tag: Composer
tag: Performer
tag: Disc
tag: Label
tag: MUSICBRAINZ_ARTISTID
tag: MUSICBRAINZ_ALBUMID
tag: MUSICBRAINZ_ALBUMARTISTID
tag: MUSICBRAINZ_TRACKID
tag: MUSICBRAINZ_RELEASETRACKID
tag: MUSICBRAINZ_WORKID
info_end
''')

    path_cursor = []
    for (path,
         length,
         artist,
         album,
         albumartist,
         title,
         track,
         genre,
         year,
         disc,
         composer,
         arranger) in cursor:
        # `genre` can be multi-valued, so rename it to `genres` for clarity while parsing.
        if genre:
            genres = genre.split(GENRE_DELIMITER)
        else:
            genres = ''

        if isinstance(path, bytes):
            path = path.decode('utf-8')

        album_directory = ospath.dirname(path[len(MUSIC_ROOT_DIR):]).lstrip(ospath.sep)
        albumdir_parts = album_directory.split(ospath.sep)

        if path_cursor != albumdir_parts:
            if path_cursor:
                first_diff_idx = [x[0]==x[1] for x in zip(albumdir_parts, path_cursor)].index(False)

                # If album changed, close the necessary directories.
                for i, p in enumerate(path_cursor[:first_diff_idx-len(path_cursor)-1:-1]):
                    tagcache_filehandle.write(f'''\
end: {os.sep.join(path_cursor[:len(path_cursor)-i])}
''')

            # If album changed, open the necessary new blocks.
            start_idx = first_diff_idx if path_cursor else 0
            for i, p in enumerate(albumdir_parts[start_idx:]):
                path_ = os.sep.join(albumdir_parts[:start_idx+i+1])
                tagcache_filehandle.write(f'''\
directory: {p}
mtime: 0
begin: {path_}
''')
            path_cursor = albumdir_parts

        # Write song block.
        tagcache_filehandle.write(f'''\
song_begin: {path.split(ospath.sep)[-1]}
Time: {length:.6f}
Artist: {artist}
Album: {album}
AlbumArtist: {albumartist}
Title: {title}
Track: {track}
''')
        for genre_value in genres:
            tagcache_filehandle.write(f'Genre: {genre_value}' + os.linesep)
        tagcache_filehandle.write(f'''\
Date: {year}
Disc: {disc}
Composer: {composer}
Performer: {arranger}
mtime: 0
song_end
''')

    # Close final directories.
    for i, _ in enumerate(path_cursor[::-1]):
        tagcache_filehandle.write(f'''\
end: {os.sep.join(path_cursor[:len(path_cursor)-i])}
''')


    # Cleanup.
    cursor.close()
    db_connection.close()
    tagcache_filehandle.close()

    endtime = time.time()
    print('It took {:.3f} seconds.'.format(endtime-starttime))
