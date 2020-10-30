import requests
import json
import random

_API_AUTHORIZATION_HEADER = 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'


class Twitter:    
    def __init__(self):
        self.host = 'https://twitter.com/' # Twitter host web version
        self.mobileHost = 'https://mobile.twitter.com/' # Twitter host mobile version
        self.helpHost = 'https://help.twitter.com/' # Twitter Helping center host
        self.API_HOST = 'https://api.twitter.com' # Twitter API host
        self.API_VERSION = "1.1"
        self.API_VERSION2 = "2"
        self._baseUrl = self.host
        self.i = 0
        self._guestToken = None
        self._userAgent = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.{random.randint(0, 9999)} Safari/537.{random.randint(0, 99)}'
        self._apiHeaders = {
            'User-Agent': self._userAgent,
            'Authorization': _API_AUTHORIZATION_HEADER,
            'Referer': self._baseUrl,
        }

    def _get_api_url(self,end_point):
        return "%s/%s/%s" % (self.API_HOST, self.API_VERSION, end_point)
    
    def _get_api_url2(self,end_point):
        return "%s/%s/%s" % (self.API_HOST, self.API_VERSION2, end_point)    
  
    def guest_token(self, url = None):
        if self._guestToken is not None:
            return
       
        response = requests.post('https://api.twitter.com/1.1/guest/activate.json', headers=self._apiHeaders)
        self._guestToken = response.json()["guest_token"]       

        if self._guestToken:
            self._apiHeaders['x-guest-token'] = self._guestToken
            return    
        
    def get_user_id(self,username):
        url = self._get_api_url("users/show.json?screen_name=%s") % username
        response_user = self._get_api_data(url)
        user_id = response_user["id"]       
        return user_id
    
    def _get_api_data(self, endpoint, params = {}):
        self.guest_token()
        response = requests.get(endpoint, params = params, headers = self._apiHeaders)
        try:
            obj = response.json()
        except json.JSONDecodeError as e:
            print(e)
        return obj     
    
    def get_items(self,account_id, cursor = 0):
        url = self._get_api_url2("timeline/profile/%s.json") % account_id
      
        query_data = {
            "include_profile_interstitial_type": "1",
            "include_blocking": "1",
            "include_blocked_by": "1",
            "include_followed_by": "1",
            # "include_want_retweets": "1",
            "include_mute_edge": "1",
            "include_can_dm": "1",
            # "include_can_media_tag": "1",
            "skip_status": "1",
            "cards_platform": "Web-12",
            "include_cards": "1",
            "include_composer_source": "true",
            "include_ext_alt_text": "true",
            # "include_reply_count": "1",
            "tweet_mode": "extended",
            "include_entities": "false",
            "include_tweet_replies": "true",
            # "include_user_entities": "true",
            # "include_ext_media_color": "true",
            # "include_ext_media_availability": "true",
            "send_error_codes": "1",
            "simple_quoted_tweets": "1",
            "count": "100",
            "ext": "mediaStats,cameraMoment",
        }
        if cursor:
            query_data["cursor"] = cursor            

        return self._iter_api_data(url, query_data)
    
    def _iter_api_data(self, endpoint, params):        
        reqParams = params
        stopOnEmptyResponse = False
        cursor = None
        while True:
            obj = self._get_api_data(endpoint, reqParams)
            self._instructions_to_tweets(obj)                 

            newCursor = None
            for instruction in obj['timeline']['instructions']:
                if 'addEntries' in instruction:
                    entries = instruction['addEntries']['entries']
                elif 'replaceEntry' in instruction:
                    entries = [instruction['replaceEntry']['entry']]
                else:
                    continue
                for entry in entries:
                    if entry['entryId'] == 'sq-cursor-bottom' or entry['entryId'].startswith('cursor-bottom-'):
                        newCursor = entry['content']['operation']['cursor']['value']
                        if 'stopOnEmptyResponse' in entry['content']['operation']['cursor']:
                            stopOnEmptyResponse = entry['content']['operation']['cursor']['stopOnEmptyResponse']
            if not newCursor or newCursor == cursor or (stopOnEmptyResponse and self._count_tweets(obj) == 0):
                break
            cursor = newCursor
            reqParams =params.copy()
            reqParams['cursor'] = cursor            

    def _count_tweets(self, obj):
        count = 0
        for instruction in obj['timeline']['instructions']:
            if 'addEntries' in instruction:
                entries = instruction['addEntries']['entries']
            elif 'replaceEntry' in instruction:
                entries = [instruction['replaceEntry']['entry']]
            else:
                continue
            for entry in entries:
                if entry['entryId'].startswith('sq-I-t-') or entry['entryId'].startswith('tweet-'):
                    count += 1
        return count            

    def _instructions_to_tweets(self, obj):
        for instruction in obj['timeline']['instructions']:
            if 'addEntries' in instruction:
                entries = instruction['addEntries']['entries']
            elif 'replaceEntry' in instruction:
                entries = [instruction['replaceEntry']['entry']]
            else:
                continue            
            
            for entry in entries:
                if entry['entryId'].startswith('sq-I-t-') or entry['entryId'].startswith('tweet-'):
                    self.i = self.i + 1
                    if 'tweet' in entry['content']['item']['content']:
                        if 'promotedMetadata' in entry['content']['item']['content']['tweet']: # Promoted tweet aka ads
                            continue
                        if entry['content']['item']['content']['tweet']['id'] not in obj['globalObjects']['tweets']:
                            print(f'Skipping tweet {entry["content"]["item"]["content"]["tweet"]["id"]} which is not in globalObjects')
                            continue
                        tweet = obj['globalObjects']['tweets'][entry['content']['item']['content']['tweet']['id']]
                    elif 'tombstone' in entry['content']['item']['content'] and 'tweet' in entry['content']['item']['content']['tombstone']:
                        if entry['content']['item']['content']['tombstone']['tweet']['id'] not in obj['globalObjects']['tweets']:
                            print(f'Skipping tweet {entry["content"]["item"]["content"]["tombstone"]["tweet"]["id"]} which is not in globalObjects')
                            continue
                        tweet = obj['globalObjects']['tweets'][entry['content']['item']['content']['tombstone']['tweet']['id']]
                    else:
                        raise Exception(f'Unable to handle entry {entry["entryId"]!r}')
                    self._tweet_to_tweet(tweet, self.i)    
    
    def _tweet_to_tweet(self, tweet, i):
        print(str(i) + "-" + tweet['full_text'])
        
        if 'extended_entities' in tweet and 'media' in tweet['extended_entities']:
            media = []
            for medium in tweet['extended_entities']['media']:
                if medium['type'] == 'photo':
                    if '.' not in medium['media_url_https']:
                        print(f'Skipping malformed medium URL on tweet {kwargs["id"]}: {medium["media_url_https"]!r} contains no dot')
                        continue
                    baseUrl, format = medium['media_url_https'].rsplit('.', 1)
                    if format not in ('jpg', 'png'):
                        print(f'Skipping photo with unknown format on tweet {kwargs["id"]}: {format!r}')
                        continue
                    media.append(tuple([f'{baseUrl}?format={format}&name=small', f'{baseUrl}?format={format}&name=large']))
                elif medium['type'] == 'video' or medium['type'] == 'animated_gif':
                    variants = []
                    for variant in medium['video_info']['variants']:
                        variants.append(tuple([variant['content_type'], variant['url'], variant.get('bitrate') or None]))
                    mKwargs = {
                        'thumbnailUrl': medium['media_url_https'],
                        'variants': variants,
                    }
                    if medium['type'] == 'video':
                        mKwargs['duration'] = medium['video_info']['duration_millis'] / 1000
                    elif medium['type'] == 'animated_gif':
                        mKwargs['duration'] = "giff"
                    
                       
                    media.append(mKwargs)
            if media:
                print(media)        
        

        print("**********-------------------****************")
    
    def main(self):
        
        user_id = self.get_user_id("drfahrettinkoca")
        self.get_items(user_id)    


if __name__ == "__main__":
    Twitter().main()
