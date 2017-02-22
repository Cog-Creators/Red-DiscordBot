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
#import time
#import logging
#import aiohttp

try:
    from PIL import Image, ImageDraw, ImageFont, ImageColor, ImagePath
    pil_available = True
except:
    pil_available = False
    
"""
identicon.py is Licesensed under FreeBSD License.
(http://www.freebsd.org/copyright/freebsd-license.html)
Copyright 1994-2009 Shin Adachi. All rights reserved.
#Python 2
https://pypi.python.org/pypi/identicon
https://github.com/shnjp/identicon
#Python 3
https://github.com/Canule/identicon
"""

__author__ = "Controller Network"
__version__ = "0.0.1"
#__all__ = ['render_identicon', 'IdenticonRendererBase']

DIR_DATA = "data/identicon/"

class Matrix2D(list):
    """Matrix for Patch rotation"""
    def __init__(self, initial=[0.] * 9):
        assert isinstance(initial, list) and len(initial) == 9
        list.__init__(self, initial)

    def clear(self):
        for i in xrange(9):
            self[i] = 0.

    def set_identity(self):
        self.clear()
        for i in xrange(3):
            self[i] = 1.

    def __str__(self):
        return "[%s]" % ", ".join("%3.2f" % v for v in self)

    def __mul__(self, other):
        r = []
        if isinstance(other, Matrix2D):
            for y in range(3):
                for x in range(3):
                    v = 0.0
                    for i in range(3):
                        v += (self[i * 3 + x] * other[y * 3 + i])
                    r.append(v)
        else:
            raise NotImplementedError
        return Matrix2D(r)

    def for_PIL(self):
        return self[0:6]

    @classmethod
    def translate(kls, x, y):
        return kls([1.0, 0.0, float(x),
                    0.0, 1.0, float(y),
                    0.0, 0.0, 1.0])

    @classmethod
    def scale(kls, x, y):
        return kls([float(x), 0.0, 0.0,
                    0.0, float(y), 0.0,
                    0.0, 0.0, 1.0])

    """
    # need `import math`
    @classmethod
    def rotate(kls, theta, pivot=None):
        c = math.cos(theta)
        s = math.sin(theta)

        matR = kls([c, -s, 0., s, c, 0., 0., 0., 1.])
        if not pivot:
            return matR
        return kls.translate(-pivot[0], -pivot[1]) * matR *
            kls.translate(*pivot)
    """
    
    @classmethod
    def rotateSquare(kls, theta, pivot=None):
        theta = theta % 4
        c = [1., 0., -1., 0.][theta]
        s = [0., 1., 0., -1.][theta]

        matR = kls([c, -s, 0., s, c, 0., 0., 0., 1.])
        if not pivot:
            return matR
        return kls.translate(-pivot[0], -pivot[1]) * matR * \
            kls.translate(*pivot)


class IdenticonRendererBase(object):
    PATH_SET = []
    
    def __init__(self, code):
        """
        @param code code for icon
        """
        if not isinstance(code, int):
            code = int(code)
        self.code = code
    
    def render(self, size):
        """
        render identicon to PIL.Image
        
        @param size identicon patchsize. (image size is 3 * [size])
        @return PIL.Image
        """
        
        # decode the code
        middle, corner, side, foreColor, backColor = self.decode(self.code)

        # make image        
        image = Image.new("RGB", (size * 3, size * 3))
        draw = ImageDraw.Draw(image)
        
        # fill background
        draw.rectangle((0, 0, image.size[0], image.size[1]), fill=0)
        
        kwds = {
            "draw": draw,
            "size": size,
            "foreColor": foreColor,
            "backColor": backColor}
        # middle patch
        self.drawPatch((1, 1), middle[2], middle[1], middle[0], **kwds)

        # side patch
        kwds["type"] = side[0]
        for i in range(4):
            pos = [(1, 0), (2, 1), (1, 2), (0, 1)][i]
            self.drawPatch(pos, side[2] + 1 + i, side[1], **kwds)
        
        # corner patch
        kwds["type"] = corner[0]
        for i in range(4):
            pos = [(0, 0), (2, 0), (2, 2), (0, 2)][i]
            self.drawPatch(pos, corner[2] + 1 + i, corner[1], **kwds)
        
        return image
                
    def drawPatch(self, pos, turn, invert, type, draw, size, foreColor,
            backColor):
        """
        @param size patch size
        """
        path = self.PATH_SET[type]
        if not path:
            # blank patch
            invert = not invert
            path = [(0., 0.), (1., 0.), (1., 1.), (0., 1.), (0., 0.)]
        patch = ImagePath.Path(path)
        if invert:
            foreColor, backColor = backColor, foreColor
        
        mat = Matrix2D.rotateSquare(turn, pivot=(0.5, 0.5)) *\
              Matrix2D.translate(*pos) *\
              Matrix2D.scale(size, size)
        
        patch.transform(mat.for_PIL())
        draw.rectangle((pos[0] * size, pos[1] * size, (pos[0] + 1) * size,
            (pos[1] + 1) * size), fill=backColor)
        draw.polygon(patch, fill=foreColor, outline=foreColor)

    ### virtual functions
    def decode(self, code):
        raise NotImplementedError


class DonRenderer(IdenticonRendererBase):
    """
    Don Park's implementation of identicon
    see : http://www.docuverse.com/blog/donpark/2007/01/19/identicon-updated-and-source-released
    """
    
    PATH_SET = [
        [(0, 0), (4, 0), (4, 4), (0, 4)],   # 0
        [(0, 0), (4, 0), (0, 4)],
        [(2, 0), (4, 4), (0, 4)],
        [(0, 0), (2, 0), (2, 4), (0, 4)],
        [(2, 0), (4, 2), (2, 4), (0, 2)],   # 4
        [(0, 0), (4, 2), (4, 4), (2, 4)],
        [(2, 0), (4, 4), (2, 4), (3, 2), (1, 2), (2, 4), (0, 4)],
        [(0, 0), (4, 2), (2, 4)],
        [(1, 1), (3, 1), (3, 3), (1, 3)],   # 8   
        [(2, 0), (4, 0), (0, 4), (0, 2), (2, 2)],
        [(0, 0), (2, 0), (2, 2), (0, 2)],
        [(0, 2), (4, 2), (2, 4)],
        [(2, 2), (4, 4), (0, 4)],
        [(2, 0), (2, 2), (0, 2)],
        [(0, 0), (2, 0), (0, 2)],
        []]                                 # 15
    MIDDLE_PATCH_SET = [0, 4, 8, 15]
    
    # modify path set
    for idx in range(len(PATH_SET)):
        if PATH_SET[idx]:
            p = list (map(lambda vec: (vec[0] / 4.0, vec[1] / 4.0), PATH_SET[idx]))
            PATH_SET[idx] = p + p[:1]
    
    def decode(self, code):
        # decode the code        
        middleType = self.MIDDLE_PATCH_SET[code & 0x03]
        middleInvert = (code >> 2) & 0x01
        cornerType = (code >> 3) & 0x0F
        cornerInvert= (code >> 7) & 0x01
        cornerTurn = (code >> 8) & 0x03
        sideType = (code >> 10) & 0x0F
        sideInvert = (code >> 14) & 0x01
        sideTurn = (code >> 15) & 0x03
        blue = (code >> 16) & 0x1F
        green = (code >> 21) & 0x1F
        red = (code >> 27) & 0x1F

        def seeded_pigment(pigment):
            random.seed(pigment)
            pigment = random.randint(0, 255)            
            return pigment
        
        foreColor = (red << 3, green << 3, blue << 3)
        #print (foreColor)
        backColor = (seeded_pigment(red), seeded_pigment(green), seeded_pigment(blue))
        #print (backColor)
            
        return (middleType, middleInvert, 0),\
               (cornerType, cornerInvert, cornerTurn),\
               (sideType, sideInvert, sideTurn),\
               foreColor, backColor#ImageColor.getrgb('white')


def render_identicon(code, size, renderer=None):
    if not renderer:
        renderer = DonRenderer
    return renderer(code).render(size)

class Identicon:
    """Identication"""
    
    def __init__(self, bot):
        self.bot = bot   

    @commands.command(pass_context=True, no_pm=False)
    async def identicon(self, ctx, user : discord.Member=None):
        """Generate an unique avatar of your Discord ID"""
        if user != None:
            user = user
            user_id = user.id
        else:
            user = ctx.message.author
            user_id = ctx.message.author.id
        channel = ctx.message.channel
        
        # Prepare
        filename = DIR_DATA+"ID-"+str(user_id)+".png"
        seed = round(int(user_id)/40000)
        
        # Generate
        result = render_identicon(seed, 200)

        # Save and send
        result.save(filename, "PNG", quality=100)
        await self.bot.send_file(channel, filename)

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Set-up
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def check_folders():
    if not os.path.exists(DIR_DATA):
        print("Creating {} folder...".format(DIR_DATA))
        os.makedirs(DIR_DATA) 
        
def setup(bot):
    check_folders()
    if pil_available is False:
        raise RuntimeError("You don't have Pillow installed, run\n```pip3 install pillow```And try again")
        return    
    bot.add_cog(Identicon(bot))
        
