import json
from requests_oauthlib import OAuth1Session
import pandas as pd
import numpy as np
import setting


def get_friends_followers_list(screen_names, twitter):
    friends_url = "https://api.twitter.com/1.1/friends/ids.json"
    followers_url = "https://api.twitter.com/1.1/followers/ids.json"
    followers = {}
    friends = {}
    for name in screen_names:
        followers[name] = []
        friends[name] = []
        param = {
            "screen_name": name,
            "count": 5000,
            "cursor": -1,
            "stringify_ids": True
        }
        while param["cursor"] != 0:
            res = twitter.get(friends_url, params=param)
            data = json.loads(res.text)
            (friends[name]).extend(data["ids"])
            param["cursor"] = data["next_cursor"]
        param["cursor"] = -1
        while param["cursor"] != 0:
            res = twitter.get(followers_url, params=param)
            data = json.loads(res.text)
            (followers[name]).extend(data["ids"])
            param["cursor"] = data["next_cursor"]
    return friends, followers


def get_follow_back_probability_indicator(followers, friends, twitter):
    screen_names = friends.keys()
    unifriends = []
    for i in friends.values():
        unifriends.extend(i)
    unifriends = list(set(unifriends))
    df = pd.DataFrame(np.zeros([len(unifriends), 2]), index=unifriends, columns=["back", "ign"])
    for name in screen_names:
        for user in friends[name]:
            if user in followers[name]:
                df.at[user, "back"] += 1
            else:
                df.at[user, "ign"] += 1
    return df.sort_values(by=["back", "ign"], ascending=[False, True])


def add_users_to_list_by_ids(owner_screen_name, slug, ids, twitter):
    n = int((len(ids)+99) / 100)
    for i in range(n):
        param = {
            "slug": slug,
            "owner_screen_name": owner_screen_name,
            "user_id" : ",".join(ids[i*100:i*100 + 100])
        }
        if i == n - 1:
            param["user_id"] = ",".join(ids[i*100:])
        twitter.post("https://api.twitter.com/1.1/lists/members/create_all.json", params=param)


def remove_users_who_follow_me_from_list(owner_screen_name, slug, twitter):
    members = []
    remove_members = []
    param = {
        "slug": slug,
        "owner_screen_name": owner_screen_name,
        "count": 5000,
        "skip_status": True
    }
    res = twitter.get("https://api.twitter.com/1.1/lists/members.json", params=param)
    data = json.loads(res.text)
    for user in data["users"]:
        members.append(user["id_str"])
    friends, followers = get_friends_followers_list([owner_screen_name], twitter)
    for member in members:
        if member in followers[owner_screen_name]:
            remove_members.append(member)
    n = int((len(remove_members)+99) / 100)
    for i in range(n):
        param = {
            "slug": slug,
            "owner_screen_name": owner_screen_name,
            "user_id" : ",".join(remove_members[i*100:i*100 + 100])
        }
        if i == n - 1:
            param["user_id"] = ",".join(remove_members[i*100:])
        twitter.post("https://api.twitter.com/1.1/lists/members/destroy_all.json", params=param)
            
    

def convert_ids_to_screen_name(ids, twitter):
    n = int((len(ids)+99) / 100)
    screen_names = []
    for i in range(n):
        param = {
            "user_id" : ",".join(ids[i*100:i*100 + 100]),
            "tweet_mode" : False
            }
        if i == n - 1:
            param["user_id"] = ",".join(ids[i*100:])
        # 900 requests per 15 minutes (user auth)
        res = twitter.post("https://api.twitter.com/1.1/users/lookup.json",
                        params=param)
        if res.status_code != 200:
            print("request error:" + str(res.status_code))
            break
        else:
            data = json.loads(res.text)
            for user in data:
                screen_names.append(user["screen_name"])
    return screen_names


if __name__ == "__main__":
    twitter = OAuth1Session(
        setting.API_KEY, setting.API_SECRET,
        setting.ACCESS_TOKEN, setting.ACCESS_TOKEN_SECRET
    )
    #remove_users_who_follow_me_from_list("", "", twitter)
    friends, followers = get_friends_followers_list(["", "", ""], twitter)
    df = get_follow_back_probability_indicator(followers, friends, twitter)
    add_users_to_list_by_ids("", "", df[(df.back==2.0) & (df.ign==0.0)].index, twitter)

