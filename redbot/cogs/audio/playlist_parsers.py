import re
from xml.dom import minidom

__all__ = ["PLSParser", "XMLParser", "M3UParser", "XSPFParser", "TXTParser"]
_RE_PARSE_URL = re.compile(r" parseUrl=\d")


class TXTParser:
    @staticmethod
    def parse(file, encoding, trackObject, playlistObject):
        playlist = list()

        lines = file.splitlines()

        i = 1
        while "" in lines:
            lines.remove("")
            i = i + 1

        for line in lines:
            fileref = line

            if fileref is not None:
                playlist.append(trackObject(File=fileref))
                # noinspection PyUnusedLocal
                fileref = None

        return playlistObject(Tracks=playlist, Encoding=encoding)


class PLSParser:
    Keys = ["File", "Title", "Length"]
    genKeys = dict()

    @staticmethod
    def ini_parse(data):
        result = dict()
        lines = data.splitlines()
        for line in lines:
            parts = line.split("=")
            if len(parts) == 2:
                result[parts[0]] = parts[1]
        return result

    def mk_keys(self, cursor):
        c_keys = list()
        for key in self.Keys:
            c_keys.append(key + str(cursor))
            self.genKeys[key + str(cursor)] = key
        return c_keys

    def get_key_name(self, genKey):
        return self.genKeys[genKey]

    def parse(self, data, encoding, trackObject, playlistObject):
        playlist = list()
        data = self.ini_parse(data)

        finish = False
        cursor = 1
        while not finish:
            keys = self.mk_keys(cursor)
            result = dict()
            for key in keys:
                try:
                    result[self.get_key_name(key)] = data[key]
                except KeyError:
                    pass
            if len(result) > 0:
                try:
                    playlist.append(
                        trackObject(
                            Name=result["Title"],
                            Duration=int(result["Length"]),
                            File=result["File"],
                        )
                    )
                except KeyError:
                    pass
                cursor = cursor + 1
            else:
                finish = True

        return playlistObject(Tracks=playlist, Encoding=encoding)


class XMLParser:
    @staticmethod
    def parse(data, trackObject, playlistObject):
        dom = minidom.parseString(data)

        tracks = (
            dom.getElementsByTagName("dict")[0]
            .getElementsByTagName("dict")[0]
            .getElementsByTagName("dict")
        )
        playlist = list()
        for track in tracks:
            t = trackObject()
            items = track.getElementsByTagName("key")
            for item in items:
                key = item.childNodes[0].nodeValue
                if not item.nextSibling.childNodes:
                    continue
                value = item.nextSibling.childNodes[0].nodeValue
                if key == "Artist":
                    t.Artist = value
                if key == "Name":
                    t.Title = value
                if key == "Location":
                    t.File = value
                if key == "Total Time":
                    t.Duration = int(value)
                if key == "Album":
                    t.Album = value
                playlist.append(t)

        return playlistObject(Tracks=playlist, Encoding="utf-8")


class XSPFParser:
    playlist = list()

    def parse(self, data, trackObject, playlistObject):
        dom = minidom.parseString(data)

        tracks = dom.getElementsByTagName("trackList")[0].getElementsByTagName("track")
        for track in tracks:
            t = trackObject()
            for item in track.childNodes:
                key = item.nodeName
                # noinspection PyBroadException
                try:
                    value = item.childNodes[0].nodeValue
                    if key == "creator":
                        t.Artist = value
                    if key == "title":
                        t.Title = value
                    if key == "location":
                        t.File = value
                    if key == "duration":
                        t.Duration = int(value)
                    if key == "album":
                        t.Album = value
                    self.playlist.append(t)
                except Exception:
                    pass
        return playlistObject(Tracks=self.playlist, Encoding="utf-8")


class M3UParser:
    @staticmethod
    def parse(file, encoding, trackObject, playlistObject):
        playlist = list()

        lines = file.splitlines()
        lines.pop(0)

        i = 1
        while "" in lines:
            lines.remove("")
            i = i + 1

        info = None
        fileref = None

        for line in lines:
            if len(line.split(u"#EXTINF:")) == 2:
                info = line.split(u"#EXTINF:")[1]
            elif len(line.split(u"#EXT-X-STREAM-INF:")) == 2:
                info = line.split(u"#EXT-X-STREAM-INF:")[1]
            else:
                fileref = line

            if info is not None and fileref is not None:
                fileref = re.sub(_RE_PARSE_URL, "", fileref)
                if "=" not in info:
                    info = info.split(",")
                    length = int(info[0])
                    name = info[1]
                else:
                    name = None
                    length = None
                playlist.append(trackObject(Name=name, Duration=length, File=fileref))
                info = None
                fileref = None

        return playlistObject(Tracks=playlist, Encoding=encoding)
