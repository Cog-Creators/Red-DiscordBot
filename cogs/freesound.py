from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from __main__ import settings as bot_settings
# Sys.
import discord
from discord.ext import commands
from operator import itemgetter, attrgetter
#from copy import deepcopy
import random
import os
import sys
import shutil
import re
import json
import glob
import subprocess
import logging
import asyncio
import errno
#import aiohttp
from urllib.request import urlopen, FancyURLopener, Request
from urllib.parse import urlparse, urlencode, quote
from urllib.error import HTTPError

# Prefer C-based ElementTree
try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

try:
    import mutagen
    from mutagen.flac import FLAC
    mutagen_available = True
except:
    mutagen_available = None

# Check for numpy lib
try:
    import numpy
    numpy_available = True
except:
    numpy_available = None

# Check for matplot lib
try:
    import matplotlib.pyplot as matplot
    import matplotlib.cbook as cbook
    import matplotlib.image as image
    matplot_available = True
except:
    matplot_available = None



log = logging.getLogger("marvin.freesound")
log.setLevel(logging.DEBUG)

__author__ = "Controller Network"
__version__ = "0.0.3"

# ToDo:
# get and move soundpacks from freesound user
# ...

# Known Issue's:
# freesound-python fails when results contain "/"

DIR_DATA = "data/freesound"
DIR_TMP = DIR_DATA+"/tmp/"
SETTINGS = DIR_DATA+"/settings.json"
AUDIO_SFX_HIERARCHY = DIR_DATA+"/audio_sfx_freesound_hierarchy.json"
DIR_AUDIO_SFX = "data/audio/sfx/freesound/"
BACKGROUND = "/data/freesound/bg.png"

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Plotbitrate - https://github.com/zeroepoch/plotbitrate
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def plot_bitrate(adur, input, stream, output, format, min:int = None, max:int =None):
        #plotbitrate.py "0004 - Pink Floyd - Comfortably Numb - 06-49.flac" -s audio -o test.png -f png

        # get list of supported matplotlib formats
        format_list = list(
            matplot.figure().canvas.get_supported_filetypes().keys())
        matplot.close()  # destroy test figure

        # check if format given w/o output file
        if format and not output:
            sys.stderr.write("Error: Output format requires output file\n")
            return False

        # check given y-axis limits
        if min and max and (min >= max):
            sys.stderr.write("Error: Maximum should be greater than minimum\n")
            return False

        bitrate_data = {}
        frame_count = 0
        frame_rate = None
        frame_time = 0.0

        # get frame data for the selected stream
        with subprocess.Popen(
            ["ffprobe",
                "-show_entries", "frame",
                "-select_streams", stream[0],
                "-print_format", "xml",
                input
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL) as proc_frame:

            # process xml elements as they close
            for event in etree.iterparse(proc_frame.stdout):

                # skip non-frame elements
                node = event[1]
                if node.tag != 'frame':
                    continue

                # count number of frames
                frame_count += 1

                # get type of frame
                if stream == 'audio':
                    frame_type = 'A'  # pseudo frame type
                else:
                    frame_type = node.get('pict_type')

                # get frame rate only once (assumes non-variable framerate)
                # TODO: use 'pkt_duration_time' each time instead
                if frame_rate is None:

                    # audio frame rate, 1 / frame duration
                    if stream == 'audio':
                        frame_rate = 1.0 / float(node.get('pkt_duration_time'))

                    # video frame rate, read stream header
                    else:
                        with subprocess.Popen(
                            ["ffprobe",
                                "-show_entries", "stream",
                                "-select_streams", "v",
                                "-print_format", "xml",
                                input
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL) as proc_stream:

                            # parse stream header xml
                            stream_data = etree.parse(proc_stream.stdout)
                            stream_elem = stream_data.find('.//stream')


                            # compute frame rate from ratio
                            frame_rate_ratio = stream_elem.get('avg_frame_rate')
                            (dividend, divisor) = frame_rate_ratio.split('/')
                            frame_rate = float(dividend) / float(divisor)

                #
                # frame time (x-axis):
                #
                #   ffprobe conveniently reports the frame time position.
                #
                # frame bitrate (y-axis):
                #
                #   ffprobe reports the frame size in bytes. This must first be
                #   converted to kbits which everyone is use to. To get instantaneous
                #   frame bitrate we must consider the frame duration.
                #
                #   bitrate = (kbits / frame) * (frame / sec) = (kbits / sec)
                #

                # collect frame data
                try:
                    frame_time = float(node.get('best_effort_timestamp_time'))
                except:
                    try:
                        frame_time = float(node.get('pkt_pts_time'))
                    except:
                        if frame_count > 1:
                            frame_time += float(node.get('pkt_duration_time'))

                frame_bitrate = (float(node.get('pkt_size')) * 8 / 1000) * frame_rate
                frame = (frame_time, frame_bitrate)

                # create new frame list if new type
                if frame_type not in bitrate_data:
                    bitrate_data[frame_type] = []

                # append frame to list by type
                bitrate_data[frame_type].append(frame)

            # check if ffprobe was successful
            if frame_count == 0:
                sys.stderr.write("Error: No frame data, failed to execute ffprobe\n")
                return False

        # end frame subprocess

        # setup new figure
        fig = matplot.figure(figsize=(24, 8), dpi = 300, edgecolor='k')#.canvas.set_window_title(input)
        #matplot.figure().canvas.set_window_title(input)
        ax = fig.add_subplot(111)
        matplot.title("Stream Bitrate vs Time")
        matplot.xlabel("Time (sec)")
        matplot.ylabel("Frame Bitrate (kbit/s)")
        matplot.grid(True)

        #Set background image
        path = os.getcwd()
        datafile = cbook.get_sample_data(path+BACKGROUND, asfileobj=False)
        #print('loading %s' % datafile)
        im = image.imread(datafile)
        im[:, :, -1] = 1.0  # set the alpha channel
        fig.figimage(im, 0, 0)

        # map frame type to color
        frame_type_color = {
            # audio
            'A': '#7289DA',
            # video
            'I': 'red',
            'P': 'green',
            'B': 'blue'
        }

        global_peak_bitrate = 0.0
        global_mean_bitrate = 0.0

        # render charts in order of expected decreasing size
        for frame_type in ['I', 'P', 'B', 'A']:

            # skip frame type if missing
            if frame_type not in bitrate_data:
                continue

            # convert list of tuples to numpy 2d array
            frame_list = bitrate_data[frame_type]
            frame_array = numpy.array(frame_list)

            # update global peak bitrate
            peak_bitrate = frame_array.max(0)[1]
            if peak_bitrate > global_peak_bitrate:
                global_peak_bitrate = peak_bitrate

            # update global mean bitrate (using piecewise mean)
            mean_bitrate = frame_array.mean(0)[1]
            global_mean_bitrate += mean_bitrate * (len(frame_list) / frame_count)

            # plot chart using gnuplot-like impulses
            matplot.vlines(
                frame_array[:,0], [0], frame_array[:,1],
                color=frame_type_color[frame_type],
                label="{} Frames".format(frame_type))

        # set y-axis limits if requested
        if min:
            matplot.ylim(ymin=min)
        if max:
            matplot.ylim(ymax=max)

        # Define step size(grid) of time axis
        step_size = round((adur*0.03)*2)/2
        print(step_size)
        ax.xaxis.set_ticks(numpy.arange(0.0, adur, step_size))

        # calculate peak line position (left 15%, above line)
        peak_text_x = matplot.xlim()[1] * 0.15
        peak_text_y = global_peak_bitrate + \
            ((matplot.ylim()[1] - matplot.ylim()[0]) * 0.015)
        peak_text = "peak ({:.0f})".format(global_peak_bitrate)

        # draw peak as think black line w/ text
        matplot.axhline(global_peak_bitrate, linewidth=2, color='blue')
        matplot.text(peak_text_x, peak_text_y, peak_text,
            horizontalalignment='center', fontweight='bold', color='blue')

        # calculate mean line position (right 85%, above line)
        mean_text_x = matplot.xlim()[1] * 0.85
        mean_text_y = global_mean_bitrate + \
            ((matplot.ylim()[1] - matplot.ylim()[0]) * 0.015)
        mean_text = "mean ({:.0f})".format(global_mean_bitrate)

        # draw mean as think black line w/ text
        matplot.axhline(global_mean_bitrate, linewidth=2, color='green')
        matplot.text(mean_text_x, mean_text_y, mean_text,
            horizontalalignment='center', fontweight='bold', color='green')

        matplot.legend()

        # render graph to file (if requested) or screen
        if output:
            matplot.savefig(output, format=format)
        else:
            matplot.show()

        # Cleanup
        del fig
        # vim: ai et ts=4 sts=4 sw=4


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Freesound-python - https://opensource.org/licenses/MIT / https://opensource.org/licenses/MIT
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class URIS():
    HOST = 'www.freesound.org'
    BASE = 'https://' + HOST + '/apiv2'
    TEXT_SEARCH = '/search/text/'
    CONTENT_SEARCH = '/search/content/'
    COMBINED_SEARCH = '/search/combined/'
    SOUND = '/sounds/<sound_id>/'
    SOUND_ANALYSIS = '/sounds/<sound_id>/analysis/'
    SIMILAR_SOUNDS = '/sounds/<sound_id>/similar/'
    COMMENTS = '/sounds/<sound_id>/comments/'
    DOWNLOAD = '/sounds/<sound_id>/download/'
    UPLOAD = '/sounds/upload/'
    DESCRIBE = '/sounds/<sound_id>/describe/'
    PENDING = '/sounds/pending_uploads/'
    BOOKMARK = '/sounds/<sound_id>/bookmark/'
    RATE = '/sounds/<sound_id>/rate/'
    COMMENT = '/sounds/<sound_id>/comment/'
    AUTHORIZE = '/oauth2/authorize/'
    LOGOUT = '/api-auth/logout/'
    LOGOUT_AUTHORIZE = '/oauth2/logout_and_authorize/'
    ME = '/me/'
    USER = '/users/<username>/'
    USER_SOUNDS = '/users/<username>/sounds/'
    USER_PACKS = '/users/<username>/packs/'
    USER_BOOKMARK_CATEGORIES = '/users/<username>/bookmark_categories/'
    USER_BOOKMARK_CATEGORY_SOUNDS = '/users/<username>/bookmark_categories/<category_id>/sounds/'  # noqa
    PACK = '/packs/<pack_id>/'
    PACK_SOUNDS = '/packs/<pack_id>/sounds/'
    PACK_DOWNLOAD = '/packs/<pack_id>/download/'

    @classmethod
    def uri(cls, uri, *args):
        for a in args:
            uri = re.sub('<[\w_]+>', quote(str(a)), uri, 1)
        return cls.BASE + uri


class FreesoundClient():
    """
    Start here, create a FreesoundClient and set an authentication token using
    set_token
    >>> c = FreesoundClient()
    >>> c.set_token("<your_api_key>")
    """
    client_secret = ""
    client_id = ""
    token = ""
    header = ""

    def get_sound(self, sound_id, **params):
        """
        Get a sound object by id
        Relevant params: descriptors, fields, normalized
        http://freesound.org/docs/api/resources_apiv2.html#sound-resources
        >>> sound = c.get_sound(6)
        """
        uri = URIS.uri(URIS.SOUND, sound_id)
        return FSRequest.request(uri, params, self, Sound)

    def text_search(self, **params):
        """
        Search sounds using a text query and/or filter. Returns an iterable
        Pager object. The fields parameter allows you to specify the
        information you want in the results list
        http://freesound.org/docs/api/resources_apiv2.html#text-search
        >>> sounds = c.text_search(
        >>>     query="dubstep", filter="tag:loop", fields="id,name,url"
        >>> )
        >>> for snd in sounds: print snd.name
        """
        uri = URIS.uri(URIS.TEXT_SEARCH)
        return FSRequest.request(uri, params, self, Pager)

    def content_based_search(self, **params):
        """
        Search sounds using a content-based descriptor target and/or filter
        See essentia_example.py for an example using essentia
        http://freesound.org/docs/api/resources_apiv2.html#content-search
        >>> sounds = c.content_based_search(
        >>>     target="lowlevel.pitch.mean:220",
        >>>     descriptors_filter="lowlevel.pitch_instantaneous_confidence.mean:[0.8 TO 1]",  # noqa
        >>>     fields="id,name,url")
        >>> for snd in sounds: print snd.name
        """
        uri = URIS.uri(URIS.CONTENT_SEARCH)
        return FSRequest.request(uri, params, self, Pager)

    def combined_search(self, **params):
        """
        Combine both text and content-based queries.
        http://freesound.org/docs/api/resources_apiv2.html#combined-search
        >>> sounds = c.combined_search(
        >>>     target="lowlevel.pitch.mean:220",
        >>>     filter="single-note"
        >>> )
        """
        uri = URIS.uri(URIS.COMBINED_SEARCH)
        return FSRequest.request(uri, params, self, CombinedSearchPager)

    def get_user(self, username):
        """
        Get a user object by username
        http://freesound.org/docs/api/resources_apiv2.html#combined-search
        >>> u=c.get_user("xserra")
        """
        uri = URIS.uri(URIS.USER, username)
        return FSRequest.request(uri, {}, self, User)

    def get_pack(self, pack_id):
        """
        Get a user object by username
        http://freesound.org/docs/api/resources_apiv2.html#combined-search
        >>> p = c.get_pack(3416)
        """
        uri = URIS.uri(URIS.PACK, pack_id)
        return FSRequest.request(uri, {}, self, Pack)

    def set_token(self, token, auth_type="token"):
        """
        Set your API key or Oauth2 token
        http://freesound.org/docs/api/authentication.html
        http://freesound.org/docs/api/resources_apiv2.html#combined-search
        >>> c.set_token("<your_api_key>")
        """
        self.token = token  # TODO
        if auth_type == 'oauth':
            self.header = 'Bearer ' + token
        else:
            self.header = 'Token ' + token


class FreesoundObject:
    """
    Base object, automatically populated from parsed json dictionary
    """
    def __init__(self, json_dict, client):
        self.client = client
        self.json_dict = json_dict

        def replace_dashes(d):
            for k, v in d.items():
                if "-" in k:
                    d[k.replace("-", "_")] = d[k]
                    del d[k]
                if isinstance(v, dict):
                    replace_dashes(v)

        replace_dashes(json_dict)
        self.__dict__.update(json_dict)
        for k, v in json_dict.items():
            if isinstance(v, dict):
                self.__dict__[k] = FreesoundObject(v, client)

    def as_dict(self):
        return self.json_dict


class FreesoundException(Exception):
    """
    Freesound API exception
    """
    def __init__(self, http_code, detail):
        self.code = http_code
        self.detail = detail

    def __str__(self):
        return '<FreesoundException: code=%s, detail="%s">' % \
                (self.code,  self.detail)


class Retriever(FancyURLopener):
    """
    Downloads previews and original sound files to disk.
    """
    def http_error_default(self, url, fp, errcode, errmsg, headers):
        resp = fp.read()
        try:
            error = json.loads(resp)
            raise FreesoundException(errcode, error.detail)
        except:
            raise Exception(resp)


class FSRequest:
    """
    Makes requests to the freesound API. Should not be used directly.
    """
    @classmethod
    def request(
            cls,
            uri,
            params={},
            client=None,
            wrapper=FreesoundObject,
            method='GET',
            data=False
            ):
        p = params if params else {}
        url = '%s?%s' % (uri, urlencode(p)) if params else uri
        d = urlencode(data) if data else None
        headers = {'Authorization': client.header}
        req = Request(url, d, headers)
        try:
            f = urlopen(req)
        except HTTPError as e:
            resp = e.read()
            if e.code >= 200 and e.code < 300:
                return resp
            else:
                raise FreesoundException(e.code, json.loads(resp))

        resp = f.read().decode("utf-8")

        f.close()
        result = None
        try:
            result = json.loads(resp)
        except:
            raise FreesoundException(0, "Couldn't parse response")
        if wrapper:
            return wrapper(result, client)
        return result

    @classmethod
    def retrieve(cls, url, client, path):
        r = Retriever()
        r.addheader('Authorization', client.header)
        return r.retrieve(url, path)


class Pager(FreesoundObject):
    """
    Paginates search results. Can be used in for loops to iterate its results
    array.
    """
    def __getitem__(self, key):
        return Sound(self.results[key], self.client)

    def next_page(self):
        """
        Get a Pager with the next results page.
        """
        return FSRequest.request(self.next, {}, self.client, Pager)

    def previous_page(self):
        """
        Get a Pager with the previous results page.
        """
        return FSRequest.request(self.previous, {}, self.client, Pager)


class GenericPager(Pager):
    """
    Paginates results for objects different than Sound.
    """
    def __getitem__(self, key):
        return FreesoundObject(self.results[key], self.client)


class CombinedSearchPager(FreesoundObject):
    """
    Combined search uses a different pagination style.
    The total amount of results is not available, and the size of the page is
    not guaranteed.
    Use :py:meth:`~freesound.CombinedSearchPager.more` to get more results if
    available.
    """
    def __getitem__(self, key):
        return Sound(self.results[key], None)

    def more(self):
        """
        Get more results
        """
        return FSRequest.request(
            self.more, {}, self.client, CombinedSearchPager
        )


class Sound(FreesoundObject):
    """
    Freesound Sound resources
    >>> sound = c.get_sound(6)
    """
    def retrieve(self, directory, name=False):
        """
        Download the original sound file (requires Oauth2 authentication).
        http://freesound.org/docs/api/resources_apiv2.html#download-sound-oauth2-required
         >>> sound.retrieve("/tmp")
        """
        path = os.path.join(directory, name if name else self.name)
        uri = URIS.uri(URIS.DOWNLOAD, self.id)
        return FSRequest.retrieve(uri, self.client, path)

    def retrieve_preview(self, directory, name=False):
        """
        Download the low quality mp3 preview.
        >>> sound.retrieve_preview("/tmp")
        """
        try:
            path = os.path.join(
                directory,
                name if name else self.previews.preview_lq_mp3.split("/")[-1])
        except AttributeError:
            raise FreesoundException(
                '-',
                'Preview uris are not present in your sound object. Please add'
                ' them using the fields parameter in your request. See '
                ' http://www.freesound.org/docs/api/resources_apiv2.html#response-sound-list.'  # noqa
            )
        return FSRequest.retrieve(
            self.previews.preview_lq_mp3,
            self.client,
            path
        )

    def get_analysis(self, descriptors=None, normalized=0):
        """
        Get content-based descriptors.
        http://freesound.org/docs/api/resources_apiv2.html#sound-analysis
        >>> a = sound.get_analysis(descriptors="lowlevel.pitch.mean")
        >>> print(a.lowlevel.pitch.mean)
        """
        uri = URIS.uri(URIS.SOUND_ANALYSIS, self.id)
        params = {}
        if descriptors:
            params['descriptors'] = descriptors
        if normalized:
            params['normalized'] = normalized
        return FSRequest.request(uri, params, self.client, FreesoundObject)

    def get_similar(self, **params):
        """
        Get similar sounds based on content-based descriptors.
        Relevant params: page, page_size, fields, descriptors, normalized,
        descriptors_filter
        http://freesound.org/docs/api/resources_apiv2.html#similar-sounds
        >>> s = sound.get_similar()
        """
        uri = URIS.uri(URIS.SIMILAR_SOUNDS, self.id)
        return FSRequest.request(uri, params, self.client, Pager)

    def get_comments(self, **params):
        """
        Get user comments.
        Relevant params: page, page_size
        http://freesound.org/docs/api/resources_apiv2.html#sound-comments
        >>> comments = sound.get_comments()
        """
        uri = URIS.uri(URIS.COMMENTS, self.id)
        return FSRequest.request(uri, params, self.client, GenericPager)

    def __repr__(self):
        return '<Sound: id="%s", name="%s">' % (self.id, self.name)


class User(FreesoundObject):
    """
    Freesound User resources.
    >>> u=c.get_user("xserra")
    """
    def get_sounds(self, **params):
        """
        Get user sounds.
        Relevant params: page, page_size, fields, descriptors, normalized
        http://freesound.org/docs/api/resources_apiv2.html#user-sounds
        >>> u.get_sounds()
        """
        uri = URIS.uri(URIS.USER_SOUNDS, self.username)
        return FSRequest.request(uri, params, self.client, Pager)

    def get_packs(self, **params):
        """
        Get user packs.
        Relevant params: page, page_size
        http://freesound.org/docs/api/resources_apiv2.html#user-packs
        >>> u.get_packs()
        """
        uri = URIS.uri(URIS.USER_PACKS, self.username)
        return FSRequest.request(uri, params, self.client, GenericPager)

    def get_bookmark_categories(self, **params):
        """
        Get user bookmark categories.
        Relevant params: page, page_size
        http://freesound.org/docs/api/resources_apiv2.html#user-bookmark-categories
        >>> u.get_bookmark_categories()
        """
        uri = URIS.uri(URIS.USER_BOOKMARK_CATEGORIES, self.username)
        return FSRequest.request(uri, params, self.client, GenericPager)

    def get_bookmark_category_sounds(self, category_id, **params):
        """
        Get user bookmarks.
        Relevant params: page, page_size, fields, descriptors, normalized
        http://freesound.org/docs/api/resources_apiv2.html#user-bookmark-category-sounds
        >>> p=u.get_bookmark_category_sounds(0)
        """
        uri = URIS.uri(
            URIS.USER_BOOKMARK_CATEGORY_SOUNDS, self.username, category_id
        )
        return FSRequest.request(uri, params, self.client, Pager)

    def __repr__(self):
        return '<User: "%s">' % self.username


class Pack(FreesoundObject):
    """
    Freesound Pack resources.
    >>> p = c.get_pack(3416)
    """
    def get_sounds(self, **params):
        """
        Get pack sounds
        Relevant params: page, page_size, fields, descriptors, normalized
        http://freesound.org/docs/api/resources_apiv2.html#pack-sounds
        >>> sounds = p.get_sounds()
        """
        uri = URIS.uri(URIS.PACK_SOUNDS, self.id)
        return FSRequest.request(uri, params, self.client, Pager)

    def __repr__(self):
        return '<Pack:  name="%s">' % self.name

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Cog
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class Freesound:
    """Freesound 'sfx' download"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO(SETTINGS, 'load')

    @commands.group(name="freesound", pass_context=True, no_pm=False)
    async def _freesound(self, ctx):
        """Freesound operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_freesound.command(pass_context=True, no_pm=False)
    @checks.admin_or_permissions(manage_server=True)
    async def apikey(self, ctx, key):
        """Set the Freesound API key."""
        user = ctx.message.author
        if self.settings["API_KEY"] != "":
            await self.bot.say("{} ` Freesound API key found, overwrite it? y/n`".format(user.mention))
            response = await self.bot.wait_for_message(author=ctx.message.author)
            if response.content.lower().strip() == "y":
                self.settings["API_KEY"] = key
                fileIO(SETTINGS, "save", self.settings)
                await self.bot.say("{} ` Freesound API key saved...`".format(user.mention))
            else:
                await self.bot.say("{} `Cancled API key opertation...`".format(user.mention))
        else:
            self.settings["API_KEY"] = key
            fileIO(SETTINGS, "save", self.settings)
            await self.bot.say("{} ` Freesound API key saved...`".format(user.mention))
        self.settings = fileIO(SETTINGS, "load")

    @_freesound.command(pass_context=True, no_pm=False)
    @checks.admin_or_permissions(manage_server=True)
    async def add(self, ctx, url):
        """Fetch sound effect files from freesound.org and put them in the general audio sfx folder"""

        url = self.strip_no_embed(url) # Clean Discord <url>

        if self.settings["API_KEY"] == "":
            await self.bot.say("Please provide an api key.")
            return
        elif not url.startswith(("http://freesound.org", "http://www.freesound.org", "https://freesound.org", "https://www.freesound.org")):
            await self.bot.say("Invalid url")
            return
        else:
            #print(url)
            key = self.settings["API_KEY"]
            freesound_client = FreesoundClient()
            freesound_client.set_token(key)

        # Parse url for sound ID
        path = urlparse(url).path  # Get the path from the URL
        path = path[path.index("sounds/"):]  # Remove everything before the 'sounds/'
        path = path[7:]  # Remove "sounds/"  at the starting of the path
        path = path.replace("/", "") # Remove "/"
        sid = path # This should be an number

        # Get sound info example
        try:
            sound = freesound_client.get_sound(sid)
        except Exception as e:
            log.debug(e)
            await self.bot.say("Something went wrong while getting data from freesound.org, check log")
            return
        sound.retrieve_preview(DIR_TMP, sound.name)
        st_ext = "err"
        # Prepare data for ffmpeg, source will usualy be wav, mp3, flac or other common type *flac in ogg container may give issue's on special operations.
        source = "{}{}".format(DIR_TMP, sound.name)
        st_path_filename, st_ext = os.path.splitext(source) # Get path / extension

        # "temp" fix when no file type given in sound.name
        if st_ext == "":
            log.debug("Unknown filetype for: ".format(url))
            st_ext = ".unknown" # for temp file, but value will be registered in metadata
            t_source = "{}{}".format(DIR_TMP, sound.name+st_ext)
            os.rename(source, t_source)
            source = t_source
            sound.name = sound.name+st_ext

        # Replace spaces and set destination form stripped path/file.ext
        no_space_dir = st_path_filename.replace(" ", "_")

        # We are gonna flac it, I don't give a flac it's flac or not, reflac the flac that ffmpeg flacs.
        destination = "{}{}".format(no_space_dir, ".flac")

        cmd_payload = 'ffmpeg -i "{0}" -acodec flac "{1}" -y -loglevel error'.format(source, destination) # call, Input, FromFile, codec, ToFile, ConfirmOverwrite, sush
        if self.ffmpeg_fcmd(cmd_payload):
            log.debug("'{}' executed with ffmpeg".format(cmd_payload))

        # Check if ffmpeg did something we like to see.
        if not os.path.exists(destination):
            log.debug("Convert to FLAC failed: {} | {}".format(source, destination))
            return
        else:
            # Remove downloaded source
            os.remove(source)
            if os.path.exists(source):
                log.debug("Failed to remove download file: {}".format(source))

        # New source from temp path/file.flac
        source = destination

        # New destination folder @ data/audio/sfx/..
        dest_folder = DIR_AUDIO_SFX+sound.username

        # Replace result name.ext to flac, since we move to another path
        no_space_name = sound.name.replace(" ", "_")
        name = no_space_name.replace(st_ext, ".flac")
        destination = "{}/{}".format(dest_folder, name)

        # Add metadata to flac, since file names are meant to be vague, and not self-explanatory at all times.
        metadata = self.add_metadata(source, sound)

        # Move file to audio/sfx/freesound/username/pack? folder.
        if not os.path.exists(dest_folder):
            print("Creating " + dest_folder + " folder...")
            os.makedirs(dest_folder)
        shutil.move(source, destination)

        # Inform requester
        await self.bot.say("File saved\n```{}\n@{}```".format(metadata, destination))

    #Soon™
    async def copy_move_tree(self, source, destination):
        ex = False
        # Copy to new path
        try:
            await self.bot.say("`Moving File:  {} to {}`".format(source, destination))
            dir = DIR_TMP+"\\"+n
            #print(dir)
            shutil.copytree(d, dir)
            cp = True
        except OSError as e:
            if sys.platform.startswith('win'):
                if isinstance(e, WindowsError) and e.winerror == 103:
                    await self.bot.say("WinError during copy code: {}".format(str(n)))
                    log.debug('uses Windows special name (%s)' % e)
                if isinstance(e, WindowsError) and e.winerror == 183:
                    await self.bot.say("WinError during copy code file/dir already exist: {}".format(str(n)))
                    log.debug('uses Windows special name file/dir exist (%s)' % n)
                # etc...
            ex = True
        # Burn the old folder
        if cp:
            try:
                await self.bot.say("`Delete {} from Import`".format(source))
                shutil.rmtree(source)
            except OSError as e:
                if sys.platform.startswith('win'):
                    log.debug(e)
                if isinstance(e, WindowsError) and e.winerror == 3:
                    await self.bot.say(" File/dir Not found: {}".format(str(n)))
                    log.debug('uses Windows special name (%s)' % e)
                # etc....
                ex = True
        if ex:
            print(":(")
            return

    def add_metadata(self, file, sound):
        # "sound" requires a "freesound_client.get_sound" object
        # http://wiki.hydrogenaud.io/index.php?title=APE_key
        try:
            # Write it
            audio = FLAC(file)
            audio["title"] = sound.name
            audio["Artist"] = sound.username
            audio["Comment"] = sound.description
            audio["Publisher"] = "freesound.org"
            audio["File"] = sound.url
            # Save it
            audio.pprint()
            audio.save()
            # Read it
            file_info = mutagen.File(file)
            log.debug("Result metadata update:")
            log.debug(file_info)
            return file_info
        except Exception as e:
            log.debug(e)
            return False

    def ffmpeg_fcmd(self, cmd):
        # Feed ffmpeg with commands
        try:
            subprocess.call(cmd, shell=True)
            return True
        except Exception as e:
            log.debug(e)
            return False

    def strip_no_embed(self, url):
        # If url contains <> get rid of it.
        if url.startswith("<") and url.endswith(">"):
            urll = len(url)
            url = url[1:]
            url = url[:urll-2]
        return url

    @_freesound.command(pass_context=True, no_pm=False)
    @checks.admin_or_permissions(manage_server=True)
    async def edit(self, ctx, file):
        channel = ctx.message.channel
        #print()
        files = []
        files = self.file_find_all(file, DIR_AUDIO_SFX)
        #print(files[0])
        if files == []:
            await self.bot.say("```No result try again.```")
        elif len(files) == 1:
            file_path = files[0]
            await self.bot.say("```File found: {}\n\nIs this the correct one? \n y/n ```".format(file_path))
            response = await self.bot.wait_for_message(author=ctx.message.author)
            response = response.content.lower().strip()

            if response.startswith(("no","n")):
                await self.bot.say("```Audio edit aborted```")
                return
            elif response.startswith(("yes","y")):
                audio_info = self.get_audio_info(files[0])
                duration = float(audio_info["format"]["duration"])

                plot = plot_bitrate(adur = duration, input = file_path, stream = "audio", output = DIR_DATA+"/tmp.png", format = "png")
                #print(type(plot))
                #print(plot)
                if plot != None:
                    await self.bot.say("```Erreur fetching plot```")
                    return
                else:
                    await self.bot.send_file(channel, DIR_DATA+"/tmp.png", content="```Analysis of audiofile: {}```".format(file_path))

                # start_from
                await self.bot.say("```OK\nThe audio file duration is: {} Sec.\nAt what time do you wanna start cutting the file? format: 00.000 seconds```".format(duration))
                response = await self.bot.wait_for_message(author=ctx.message.author)
                response = response.content.lower().strip()
                try:
                    response = float(response)
                except:
                    await self.bot.say("```Start over and try numbers```")
                    return

                if response >= duration:
                    await self.bot.say("```Start over and try a lower value```")
                    return
                elif response < 0.0:
                    await self.bot.say("```Start over and try a higher value```")
                    return
                else:
                    start_from = response

                # stop_at
                await self.bot.say("``` At what time do you wanna end cutting the file?  format: 00.000 seconds```".format(duration))
                response = await self.bot.wait_for_message(author=ctx.message.author)
                response = response.content.lower().strip()
                try:
                    response = float(response)
                except:
                    await self.bot.say("```Start over and try numbers```")
                    return

                if response <= start_from:
                    await self.bot.say("```Start over and try a higher value beyond start value: {}```".format(str(start_from)))
                    return
                elif response > duration:
                    await self.bot.say("```Start over and try a lower value than```".format(duration))
                    return
                else:
                    stop_at = response

                # Prepare data for ffmpeg, editted file will have "-edit" added to filename
                st_path_filename, st_ext = os.path.splitext(file_path) # Get path / extension
                source = st_path_filename+st_ext
                # Make sure we dont overwrite
                destination = None
                count_edits = 0
                while count_edits <= 999:
                    # Guess name for destination
                    if count_edits < 10:
                        checkFile = "{}-edit0{}{}".format(st_path_filename, count_edits, st_ext)
                    else:
                        checkFile = "{}-edit{}{}".format(st_path_filename, count_edits, st_ext)
                    # Chack and set destination
                    if not os.path.exists(checkFile):
                        # From source
                        if count_edits < 10:
                            if st_path_filename.endswith("-edit0{}".format(count_edits)):
                                destination = "{}-edit0{}.{}{}".format(st_path_filename, count_edits, 1, st_ext)
                            else:
                                destination = "{}-edit0{}{}".format(st_path_filename, count_edits, st_ext)
                        else:
                            destination = "{}-edit{}{}".format(st_path_filename, count_edits, st_ext)
                        break
                    else:
                        count_edits += 1

                cmd_payload = 'ffmpeg -ss {2} -t {3} -i "{0}" -acodec flac "{1}" -y -loglevel error'.format(source, destination, start_from, stop_at) #call, Position, duration, Input, FromFile, codec, ToFile, ConfirmOverwrite, sush
                self.ffmpeg_fcmd(cmd_payload)

                # Check if trowing shit at ffmpeg worked.
                if self.ffmpeg_fcmd(cmd_payload):
                    log.debug("'{}' executed with ffmpeg".format(cmd_payload))
                else:
                    return

                # Check if ffmpeg did something we like to see.
                if not os.path.exists(destination):
                    log.debug("Chopping audiofile failed: {} | {}".format(source, destination))
                    await self.bot.say("Chopping audiofile failed: {} | {}".format(source, destination))
                    return
                else:
                    audio_info = self.get_audio_info(destination)
                    duration = float(audio_info["format"]["duration"])
                    plot = plot_bitrate(adur = duration, input = destination, stream = "audio", output = DIR_DATA+"/tmp.png", format = "png")
                    await self.bot.send_file(channel, DIR_DATA+"/tmp.png", content="```Analysis of audiofile after edit as: {}```".format(destination))
                    await self.bot.say("```Done.\n{}```".format(destination))

    def file_find_all(self, name, path):
        result = []
        for root, dirs, files in os.walk(path):
            if name in files:
                result.append(os.path.join(root, name))
        return result

    def get_audio_info(self, path_file):
        try:
            path_file = "./"+path_file
            cmd_payload = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path_file]
            p = subprocess.Popen(cmd_payload, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            out, sp_err =  p.communicate()
            ostr = out.decode("utf-8") # Should contain str of json
            output = json.loads(ostr) # Make it json
            return output
        except Exception as e:
            print (e)
            return("??:??")
        if sp_err:
            print (sp_err)
            return("??:??")


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Set-up
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def check_ffmpeg():
    """Windows only"""
    files = ("ffmpeg", "ffprobe", "ffplay")
    if not all([shutil.which(f) for f in files]): # Return the path to an executable which would be run if the given cmd was called. If no cmd would be called, return None.
        return False
    else:
        return True

def check_folders():
    folders = (DIR_DATA, DIR_TMP, DIR_AUDIO_SFX)
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)

def check_files():

    default = {"API_KEY": ""}

    f = SETTINGS
    if not fileIO(f, "check"):
        print("Creating Freesound settings.json...")
        fileIO(f, "save", default)

def setup(bot):
    check_folders()
    check_files()
    if not check_ffmpeg():
        raise RuntimeError("ffmpeg, ffprobe and/or ffplay are missing, obtain a copy of ffmpeg add them to your sytem PATH and try again")
    if not mutagen_available:
        raise RuntimeError("mutagen is missing, do: pip3 install mutagen")
    if not numpy_available:
        raise RuntimeError("numpy is missing, get your bitness python3(cp35) numpy install package from http://www.lfd.uci.edu/~gohlke/pythonlibs/ and do: pip3 install packagename.whl in file located directory")
    if not matplot_available:
        raise RuntimeError("matplot is missing, get your bitness python3(cp35) matplotlib install package from http://www.lfd.uci.edu/~gohlke/pythonlibs/ and do: pip3 install packagename.whl in file located directory")
    bot.add_cog(Freesound(bot))
