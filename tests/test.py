# encoding: utf8

from functools import wraps
import hashlib
import pafy
import time
import os
import sys
# pafy = pafy.pafy
p = pafy.pafy
pafy = p

try:
    import unittest2 as unittest

except ImportError:
    import unittest

def stdout_to_null(fn):
    """  Supress stdout. """

    @wraps(fn)
    def wrapper(*a, **b):
        with open(os.devnull, "w") as nul:
            stash = sys.stdout
            sys.stdout = nul
            retval = fn(*a, **b)
            sys.stdout = stash
        return retval
    return wrapper


class Test(unittest.TestCase):

    def runOnce(self):
        if hasattr(Test, "hasrun"):
            return

        Test.quick = os.environ.get("quick")
        Test.videos = VIDEOS if not Test.quick else []
        Test.playlists = PLAYLISTS if not Test.quick else []

        for video in Test.videos:
            time.sleep(0 if Test.quick else self.delay)
            video['pafy'] = pafy.new(video['identifier'])
            video['streams'] = video['pafy'].streams
            video['best'] = video['pafy'].getbest()
            video['bestaudio'] = video['pafy'].getbestaudio()

        for playlist in Test.playlists:
            playlist['fetched'] = pafy.get_playlist(playlist['identifier'])

        Test.hasrun = True

    def setUp(self):
        self.delay = 3
        self.properties = ("videoid title length duration author "
                           "username category thumb published").split()
        self.runOnce()

    def get_all_funcs(self):
        mainfunc = pafy._get_mainfunc_from_js(JAVASCRIPT)
        otherfuncs = pafy._get_other_funcs(mainfunc, JAVASCRIPT)

        # store all functions in Pafy.funcmap
        pafy.Pafy.funcmap = {"jsurl": {mainfunc['name']: mainfunc}}
        pafy.Pafy.funcmap["jsurl"]["mainfunction"] = mainfunc
        for funcname, func in otherfuncs.items():
            pafy.Pafy.funcmap['jsurl'][funcname] = func

        return mainfunc, otherfuncs

    @stdout_to_null
    def test_pafy_download(self):
        """ Test downloading. """

        callback = lambda a, b, c, d, e: 0
        vid = pafy.new("DsAn_n6O5Ns", gdata=True)
        vstream = vid.audiostreams[-1]
        name = vstream.download(filepath="file/", callback=callback)
        self.assertEqual(name[0:5], "WASTE")

    def test_lazy_pafy(self):
        """ Test create pafy object without fetching data. """

        vid = pafy.new("DsAn_n6O5Ns", basic=False, signature=False)
        self.assertEqual(vid.bigthumb, '')
        self.assertEqual(vid.bigthumbhd, '')
        self.assertIsInstance(vid.likes, int)
        self.assertIsInstance(vid.dislikes, int)

    def test_pafy_init(self):
        """ Test Pafy object creation. """
        # test bad video id, 11 chars
        badid = "12345678901"
        too_short = "123"
        self.assertRaises(ValueError, pafy.new, too_short)
        self.assertRaises(ValueError, pafy.get_playlist, badid)
        self.assertRaises(IOError, pafy.new, badid)
        self.assertRaises(IOError, pafy.get_playlist, "a" * 18)

        for video in Test.videos:
            self.assertIsInstance(video['pafy'], pafy.Pafy)
            #self.assertTrue(isinstance(video['pafy'], pafy.Pafy))

    def test_video_properties(self):
        """ Test video properties. """
        for video in Test.videos:
            description = video['pafy'].description.encode("utf8")
            self.assertEqual(hashlib.sha1(description).hexdigest(),
                             video['description'])

            for prop in self.properties:
                self.assertEqual(getattr(video['pafy'], prop), video[prop])

            self.assertNotEqual(video.__repr__(), None)

    def test_streams_exist(self):
        """ Test for expected number of streams. """
        for video in Test.videos:
            paf = video['pafy']
            self.assertEqual(video['all streams'], len(paf.allstreams))
            self.assertEqual(video['normal streams'], len(paf.streams))
            self.assertEqual(video['audio streams'], len(paf.audiostreams))
            self.assertEqual(video['video streams'], len(paf.videostreams))
            self.assertEqual(video['ogg streams'], len(paf.oggstreams))
            self.assertEqual(video['m4a streams'], len(paf.m4astreams))

    def test_best_stream_size(self):
        """ Test stream filesize. """
        for video in Test.videos:
            time.sleep(0 if Test.quick else self.delay)
            size = video['best'].get_filesize()
            self.assertEqual(video['bestsize'], size)

    def test_get_other_funcs(self):
        """ Test extracting javascript functions. """
        js = "function  f$(x,y){var X=x[1];var Y=y[1];return X;}"
        primary_func = dict(body="a=f$(12,34);b=f$(56,67)")
        otherfuncs = pafy._get_other_funcs(primary_func, js)
        # otherfuncs should be:
        #{'f$': {'body': var X=x[1];var Y=y[1];return X;",
        #        'name': 'f$', 'parameters': ['x', 'y']}}
        expected_body = 'var X=x[1];var Y=y[1];return X;'
        self.assertEqual(otherfuncs['f$']['body'], expected_body)
        self.assertEqual(otherfuncs['f$']['name'], 'f$')
        self.assertEqual(otherfuncs['f$']['parameters'], ['x', 'y'])

    def test_solve(self):
        """ Test solve js function. """
        mainfunc, otherfuncs = self.get_all_funcs()
        self.assertEqual(mainfunc['name'], "mthr")
        self.assertEqual(mainfunc["parameters"], ["a"])
        self.assertGreater(len(mainfunc['body']), 3)
        #self.assertTrue(len(mainfunc['body']) > 3,
                        #"%s not greater than %s" % (len(mainfunc['body']), 3))
        self.assertIn("return", mainfunc['body'])
        self.assertEqual(otherfuncs['fkr']['parameters'], ['a', 'b'])
        # test pafy._solve
        mainfunc['args'] = {'a': "1234567890"}
        solved = pafy._solve(mainfunc, "jsurl")
        self.assertEqual(solved, "2109876752")

    def test_solve_errors(self):
        """ Test solve function exceptions. """

        mainfunc, otherfuncs = self.get_all_funcs()

        # test unknown javascript
        mainfunc['body'] = mainfunc['body'].replace("a=a.reverse()", "a=a.peverse()")
        mainfunc['args'] = dict(a="1234567890")
        self.assertRaises(IOError, pafy._solve, mainfunc, "jsurl")

        # test return statement not found
        mainfunc, otherfuncs = self.get_all_funcs()
        mainfunc['body'] = mainfunc['body'].replace("return ", "a=")
        mainfunc['args'] = dict(a="1234567890")
        self.assertRaises(IOError, pafy._solve, mainfunc, "jsurl")

    def test_decodesig(self):
        """ Test signature decryption function. """
        mainfunc, otherfuncs = self.get_all_funcs()
        pafy.new.callback = lambda x: None
        self.assertEqual('2109876752', pafy._decodesig('1234567890', 'jsurl'))
        mainfunc, otherfuncs = self.get_all_funcs()
        pafy.Pafy.funcmap["jsurl"]['mainfunction']['parameters'] = ["a", "b"]
        self.assertRaises(IOError, pafy._decodesig, '1234567890', 'jsurl')

    def test_get_playlist(self):
        """ Test get_playlist function. """

        for pl in Test.playlists:
            fetched = pl['fetched']
            self.assertEqual(len(fetched['items']), pl['count'])

            for field in "playlist_id description author title".split():
                self.assertEqual(fetched[field], pl[field])

    def test_misc_tests(self):
        """ Test extract_smap and _getval. """
        self.assertEqual(pafy._extract_smap("a", "bcd"), [])
        self.assertRaises(IOError, pafy._getval, "no_digits_here", "88")

        # _get_func_from_call
        xcaller = {"args": [1, 2, 3]}
        xname = {'parameters': [1, 2, 3]}
        xarguments = ["1", "2", "3"]
        pafy.Pafy.funcmap["js_url"] = {"hello": xname}
        pafy._get_func_from_call(xcaller, "hello", xarguments, "js_url")


JAVASCRIPT = """\
function mthr(a){a=a.split("");a=fkr(a,59);a=a.slice(1);a=fkr(a,66);\
a=a.slice(3);a=fkr(a,10);a=a.reverse();a=fkr(a,55);a=fkr(a,70);\
a=a.slice(1);return a.join("")};

function fkr(a,b){var c=a[0];a[0]=a[b%a.length];a[b]=c;return a};

z.sig||mthr(aaa.bbb)
"""


PLAYLISTS = [
    {
        'identifier': "http://www.youtube.com/playlist?list=PL91EF4BD43796A9A4",
        'playlist_id': "PL91EF4BD43796A9A4",
        'description': "",
        'author': "sanjeev virmani",
        'title': "Android Development 200 lectures",
        'count': 200,
    },
]

VIDEOS = [
    {
        'identifier': 'ukm64IUANwE',
        'videoid': 'ukm64IUANwE',
        'title': 'Getting started with automated testing',
        'length': 1838,
        'duration': '00:30:38',
        'author': 'NextDayVideo',
        'username': 'NextDayVideo',
        'published': '2013-03-19 23:43:42',
        'thumb': 'http://i1.ytimg.com/vi/ukm64IUANwE/default.jpg',
        'category': 'Education',
        'description': '1223db22b4a38d0a8ebfcafb549f40c39af26251',
        'bestsize': 54284129,
        'all streams': 10,
        'normal streams': 5,
        'video streams': 4,
        'audio streams': 1,
        'ogg streams': 0,
        'm4a streams': 1,
    },
    {
        'identifier': 'www.youtube.com/watch?v=SeIJmciN8mo',
        'videoid': 'SeIJmciN8mo',
        'title': 'Nicki Minaj - Starships (Explicit)',
        'length': 262,
        'duration': '00:04:22',
        'author': 'NickiMinajAtVEVO',
        'username': 'NickiMinajAtVEVO',
        'published': '2012-04-27 04:22:39',
        'thumb': 'http://i1.ytimg.com/vi/SeIJmciN8mo/default.jpg',
        'category': 'Music',
        'description': 'fa34f2704be9c1b21949af515e813f644f14b89a',
        'bestsize': 101836539,
        'all streams': 21,
        'normal streams': 6,
        'video streams': 13,
        'audio streams': 2,
        'ogg streams': 1,
        'm4a streams': 1,
    },
    {
        'identifier': 'https://youtu.be/watch?v=07FYdnEawAQ',
        'videoid': '07FYdnEawAQ',
        'title': 'Justin Timberlake - Tunnel Vision (Explicit)',
        'length': 420,
        'duration': '00:07:00',
        'author': 'justintimberlakeVEVO',
        'username': 'justintimberlakeVEVO',
        'published': '2013-07-03 22:00:16',
        'thumb': 'http://i1.ytimg.com/vi/07FYdnEawAQ/default.jpg',
        'category': 'Music',
        'description': '55e8e6e2b219712bf94d67c2434530474a503265',
        'bestsize': 80664244,
        'all streams': 21,
        'normal streams': 6,
        'video streams': 13,
        'audio streams': 2,
        'ogg streams': 1,
        'm4a streams': 1,
    },
    {
        'identifier': 'EnHp24CVORc',
        'videoid': 'EnHp24CVORc',
        'title': 'Chinese Knock Off Sky Loop Roller Coaster POV Chuanlord Holiday Manor China 魔环垂直过山车',
        'length': 313,
        'duration': '00:05:13',
        'author': 'Theme Park Review',
        'username': 'themeparkreviewTPR',
        'published': '2014-05-05 19:58:07',
        'thumb': 'http://i1.ytimg.com/vi/EnHp24CVORc/default.jpg',
        'category': 'People',
        'description': '3c884d9791be15646ddf351edffcb2dd22ec70f8',
        'bestsize': 103405966,
        'all streams': 19,
        'normal streams': 6,
        'video streams': 11,
        'audio streams': 2,
        'ogg streams': 1,
        'm4a streams': 1,
    },
    {
        'identifier': 'Wbohqf64mNA',
        'videoid': 'Wbohqf64mNA',
        'title': 'EXO-K - 월광 (Moonlight) (Korean Ver.) (Full Audio) [Mini Album - Overdose]',
        'length': 266,
        'duration': '00:04:26',
        'author': 'BubbleFeetMusic Blast Channel 5 (#SpringTime)',
        'username': 'BubbleFeetBlastCH5',
        'published': '2014-05-06 13:35:09',
        'thumb': 'http://i1.ytimg.com/vi/Wbohqf64mNA/default.jpg',
        'category': 'Music',
        'description': 'eea422bad07d30339bc40f6c3df09b1125ab05e8',
        'bestsize': 8734671,
        'all streams': 17,
        'normal streams': 6,
        'video streams': 9,
        'audio streams': 2,
        'ogg streams': 1,
        'm4a streams': 1,
    }
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
    #unittest.main()
