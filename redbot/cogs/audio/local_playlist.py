from xml.dom import minidom
from random import randrange

try:
    from chardet.universaldetector import UniversalDetector

    chardet = True
except ImportError:
    chardet = False

from .playlist_parsers import *


class Track:
    def __init__(self, Artist=None, Title=None, Album=None, Name=None, Duration=None, File=None):
        self.Artist = Artist
        self.Title = Title
        self.Album = Album
        self.Name = Name
        self.Duration = Duration
        self.File = File

        self.Inverted = False

    def defineArtist(self, Artist):
        self.Artist = Artist
        if self.Inverted:
            self.Title = self.Name.split(" - " + Artist)[0]
        else:
            self.Title = self.Name.split(Artist + " - ")[1]

    def nameParse(self, invert=False):
        if invert:
            self.Inverted = True
        invert = self.Inverted

        results = list()
        splitted = self.Name.split(" - ")
        if len(splitted) == 2:
            if not invert:
                self.Artist = splitted[0]
                self.Title = splitted[1]
            else:
                self.Artist = splitted[1]
                self.Title = splitted[0]
            return True
        elif len(splitted) < 2:
            return False
        else:
            probcursor = 1
            if invert:
                splitted.reverse()
            while probcursor != len(splitted):
                artist = str()
                wordcursor = 1
                words = splitted[0:probcursor]
                if invert:
                    words.reverse()
                for part in words:
                    artist = artist + part
                    if len(words) - wordcursor > 0:
                        artist = artist + " - "
                    wordcursor = wordcursor + 1
                results.append(artist)
                probcursor = probcursor + 1
            return results

    def mustInvert(self, artist):
        if self.Name.lower().rfind(artist.lower()) > 0:
            self.Inverted = True
        else:
            self.Inverted = False
        return self.Inverted


class LocalPlaylist:
    def __init__(self, Tracks=None, Encoding=None):
        self.Tracks = Tracks
        self.Inverted = False
        self.Encoding = Encoding

    def nameParse(self, invert=False):
        for track in self.Tracks:
            track.nameParse(invert)

    def mustInvert(self, artist=None):
        if artist == None:
            self.randTracks = list()
            for i in range(0, 3, 1):
                self.randTracks.append(self.Tracks[randrange(0, len(self.Tracks) - 1)])
            return self.randTracks
        else:
            for track in self.randTracks:
                if track.mustInvert(artist):
                    for track in self.Tracks:
                        track.Inverted = True
                    self.Inverted = True
                    return True


def type_guess(data):
    lines = data.split("\n")
    if "#EXTM3U" in lines[0]:
        try:
            lines.decode("utf-8")
            return ".m3u8"
        except:
            return ".m3u"
    if "[playlist]" in lines[0]:
        return ".pls"
    dom = minidom.parseString(data)
    try:
        for namespace in dom.getElementsByTagName("playlist")[0].attributes.items():
            try:
                if namespace[1] == "http://xspf.org/ns/0/":
                    return ".xspf"
            except:
                pass
    except:
        pass
    try:
        dom.getElementsByTagName("plist")
        return ".xml"
    except:
        return None


def decode(filename, data):
    if ".m3u8" in filename:
        encoding = "utf-8"
        data = data.decode(encoding)
    elif any(i in filename for i in [".m3u", ".pls", ".txt"]):
        try:
            encoding = "ISO-8859-2"
            data = data.decode(encoding)
        except Exception:
            if chardet:
                u = UniversalDetector()
                u.feed(data)
                u.close()
                if u.result["confidence"] > 0.5:
                    try:
                        encoding = u.result["encoding"]
                        data = data.decode(encoding)
                    except:
                        encoding = "ascii"
                else:
                    encoding = "ascii"
            else:
                encoding = "ascii"
    elif ".xml" in filename or ".xspf" in filename:
        encoding = "utf-8"

    return {"data": data, "encoding": encoding}


def parse(filename=None, filedata=None, encoding=None):
    if filedata is not None:
        file = filedata
        if filename is None:
            filename = type_guess(filedata)
    else:
        f = open(filename, "rb")
        file = f.read()
        f.close()

    if encoding is None:
        decoded = decode(filename, file)
        file = decoded["data"]
        encoding = decoded["encoding"]
    else:
        try:
            file = file.decode(encoding)
        except Exception:
            decoded = decode(filename, file)
            file = decoded["data"]
            encoding = decoded["encoding"]

    if ".m3u" in filename or ".m3u8" in filename:
        m3uparser = M3UParser()
        return m3uparser.parse(file, encoding, Track, LocalPlaylist)
    if ".pls" in filename:
        plsparser = PLSParser()
        return plsparser.parse(file, encoding, Track, LocalPlaylist)
    if ".xspf" in filename:
        xspfparser = XSPFParser()
        return xspfparser.parse(file, Track, LocalPlaylist)
    if ".xml" in filename:
        xmlparser = XMLParser()
        return xmlparser.parse(file, Track, LocalPlaylist)
    if ".txt" in filename:
        txtparser = TXTParser()
        return txtparser.parse(file, encoding, Track, LocalPlaylist)
    # TODO ASL and WPL Support


for track in parse(r"D:\test\localtracks\Folder 2\playlists\sample.m3u8").__dict__["Tracks"]:
    print(track.__dict__)
