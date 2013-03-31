import ConfigParser
import HTMLParser
import twitter
import datetime, time
import logging

cfg = 'test.cfg'



def get_auth(filename=cfg):
    """
    Get an authentication object that can be passed to a twitter client.
    Note this doesn't actually check the OAuth credentials are valid.
    """

    p = ConfigParser.SafeConfigParser()
    if not p.read(filename):
        raise Exception('Invalid configuration file: %s' % filename)

    try:
        consumer_key = p.get('twitter', 'consumer_key')
        logging.debug('consumer key: %s' % consumer_key)
        consumer_secret = p.get('twitter', 'consumer_secret')
        logging.debug('consumer secret: %s' % consumer_secret)

    except (NoOptionError, NoSectionError) as e:
        raise Exception('No application consumer key/secret found, '
                        'please create one at '
                        'https://dev.twitter.com/apps/ '
                        'and edit %s' % filename)

    try:
        oauth_token = p.get('twitter', 'oauth_token')
        logging.debug('oauth_token: %s' % oauth_token)
        oauth_token_secret = p.get('twitter', 'oauth_token_secret')
        logging.debug('oauth_token_secret: %s' % oauth_token_secret)

    except ConfigParser.NoOptionError:
        logging.debug('OAuth token not found')
        oauth_token, oauth_token_secret = twitter.oauth_dance(
            'T2X', consumer_key, consumer_secret)
        p.set('twitter', 'oauth_token', oauth_token)
        p.set('twitter', 'oauth_token_secret', oauth_token_secret)
        p.write(open(filename, 'w'))

        logging.debug('oauth_token: %s' % oauth_token)
        logging.debug('oauth_token_secret: %s' % oauth_token_secret)

    auth = twitter.OAuth(oauth_token, oauth_token_secret,
                         consumer_key, consumer_secret)
    return auth


def get_client(resource=None):
    auth = get_auth()

    if resource is None:
        client = twitter.Twitter(auth=auth)
    elif resource == 'stream':
        client = twitter.TwitterStream(auth=auth)
    elif resource == 'userstream':
        client = twitter.TwitterStream(
            auth=auth, domain="userstream.twitter.com")
    else:
        raise Exception('Unknown resource')

    logging.debug('Created Twitter client')
    return tw


def format_time(dtstr):
    """
    Attempt to convert a Twitter time into the local timezone
    """
    try:
        # Assumes time is always in UTC (+0000)
        dt = datetime.datetime.strptime(dtstr, '%a %b %d %H:%M:%S +0000 %Y')
        if time.daylight:
            offset = time.altzone
        else:
            offset = time.timezone
        localdt = dt - datetime.timedelta(seconds=offset)
        s = str(localdt.time())
    except ValueError:
        s = dtstr
    return s


def format_tweet(t):
    user = t['user']['screen_name']
    text = t['text']
    urls = t['entities']['urls']
    tm = t['created_at']

    ft = text
    for u in reversed(urls):
        a = u['indices'][0]
        b = u['indices'][1]
        exp = u['expanded_url']
        ft = ft[:a] + exp + ft[b:]

    tmstr = format_time(tm)
    return '@%s: %s [%s]' % (user, HTMLParser.HTMLParser().unescape(ft), tmstr)



class MmmTwitter(object):

    def __init__(self):
        self.cbs = []
        pass

    def add_callback(self, cb):
        self.cbs.append(cb)

    def run_one(self):
        tw = get_client('userstream')
        it = tw.user()
        for t in it:
            # The first result seems to not be a tweet
            if t.has_key('friends'):
                logging.debug('Ignore result: %s' % t)
                continue

            tstr = format_tweet(t)
            for cb in self.cbs:
                logging.debug('Calling callback (%s)' % tstr)
                cb(tstr)

    def run(self):
        while True:
            try:
                self.run_one()
            except twitter.TwitterHTTPError as e:
                logging.warn('Twitter error: %s' % e)
                pass


