"""Python library allowing interaction with the Cleverbot API."""
import http.cookiejar
import hashlib
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
from urllib.parse import unquote
import html


class Cleverbot:
    """
    Wrapper over the Cleverbot API.

    """
    HOST = "www.cleverbot.com"
    PROTOCOL = "http://"
    RESOURCE = "/webservicemin"
    API_URL = PROTOCOL + HOST + RESOURCE

    headers = {
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0)',
        'Accept': 'text/html,application/xhtml+xml,'
                  'application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
        'Accept-Language': 'en-us,en;q=0.8,en-us;q=0.5,en;q=0.3',
        'Cache-Control': 'no-cache',
        'Host': HOST,
        'Referer': PROTOCOL + HOST + '/',
        'Pragma': 'no-cache'
    }

    def __init__(self):
        """ The data that will get passed to Cleverbot's web API """
        self.data = {
            'stimulus': '',
            'start': 'y',  # Never modified
            'sessionid': '',
            'vText8': '',
            'vText7': '',
            'vText6': '',
            'vText5': '',
            'vText4': '',
            'vText3': '',
            'vText2': '',
            'icognoid': 'wsf',  # Never modified
            'icognocheck': '',
            'fno': 0,  # Never modified
            'prevref': '',
            'emotionaloutput': '',  # Never modified
            'emotionalhistory': '',  # Never modified
            'asbotname': '',  # Never modified
            'ttsvoice': '',  # Never modified
            'typing': '',  # Never modified
            'lineref': '',
            'sub': 'Say',  # Never modified
            'islearning': 1,  # Never modified
            'cleanslate': False,  # Never modified
        }

        # the log of our conversation with Cleverbot
        self.conversation = []
        self.resp = str()

        # install an opener with support for cookies
        cookies = http.cookiejar.LWPCookieJar()
        handlers = [
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(),
            urllib.request.HTTPCookieProcessor(cookies)
        ]
        opener = urllib.request.build_opener(*handlers)
        urllib.request.install_opener(opener)

        # get the main page to get a cookie (see bug  #13)
        try:
            urllib.request.urlopen(Cleverbot.PROTOCOL + Cleverbot.HOST)
        except urllib.error.HTTPError:
            # TODO errors shouldn't pass unnoticed, 
            # here and in other places as well
            return str()

    def ask(self, question):
        """Asks Cleverbot a question.
        
        Maintains message history.
                                 
        Args:
            q (str): The question to ask

        Returns:
            Cleverbot's answer
        """
        # Set the current question
        self.data['stimulus'] = question

        # Connect to Cleverbot's API and remember the response
        try:
            self.resp = self._send()
        except urllib.error.HTTPError:
            # request failed. returning empty string
            return str()

        # Add the current question to the conversation log
        self.conversation.append(question)

        parsed = self._parse()

        # Set data as appropriate
        if self.data['sessionid'] != '':
            self.data['sessionid'] = parsed['conversation_id']

        # Add Cleverbot's reply to the conversation log
        self.conversation.append(parsed['answer'])

        return html.unescape(parsed['answer'])

    def _send(self):
        """POST the user's question and all required information to the 
        Cleverbot API

        Cleverbot tries to prevent unauthorized access to its API by
        obfuscating how it generates the 'icognocheck' token, so we have
        to URLencode the data twice: once to generate the token, and
        twice to add the token to the data we're sending to Cleverbot.
        """
        # Set data as appropriate
        if self.conversation:
            linecount = 1
            for line in reversed(self.conversation):
                linecount += 1
                self.data['vText' + str(linecount)] = line
                if linecount == 8:
                    break

        # Generate the token
        enc_data = urllib.parse.urlencode(self.data)
        digest_txt = enc_data[9:35]
        digest_txt = bytearray(digest_txt, 'utf-8')
        token = hashlib.md5(digest_txt).hexdigest()
        self.data['icognocheck'] = token

        # Add the token to the data
        enc_data = urllib.parse.urlencode(self.data)
        enc_data = bytearray(enc_data, 'utf-8')
        req = urllib.request.Request(self.API_URL, enc_data, self.headers)

        # POST the data to Cleverbot's API
        conn = urllib.request.urlopen(req)
        resp = conn.read()

        # Return Cleverbot's response
        return resp

    def _parse(self):
        """Parses Cleverbot's response"""
        resp = self.resp.decode('utf-8')
        parsed = [
            item.split('\r') for item in resp.split('\r\r\r\r\r\r')[:-1]
        ]
        try:
            parsed_dict = {
                'answer': parsed[0][0],
                'conversation_id': parsed[0][1],
                'conversation_log_id': parsed[0][2],
            }
        except:
            parsed_dict = {
                    'answer': parsed[0][0],
                    'conversation_id': parsed[0][1],
                    'conversation_log_id': 'not found',
                    }
        try:
            parsed_dict['unknown'] = parsed[1][-1]
        except IndexError:
            parsed_dict['unknown'] = None
        return parsed_dict
