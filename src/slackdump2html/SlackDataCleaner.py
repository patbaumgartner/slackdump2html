from typing import Tuple

from slackdump2html.data_structures import SlackData, ChannelType


class SlackDataCleaner:
    user_map: dict[str, str] = dict()
    channel_map: dict[str, Tuple[ChannelType, str]] = dict()
    emoji_skin_tones = {
        2: "_light_skin_tone",
        3: "_medium-light_skin_tone",
        4: "_medium_skin_tone",
        5: "_medium-dark_skin_tone",
        6: "_dark_skin_tone",
    }
    emoji_name_start_slack_to_lib = {
        "angel": "baby_angel",
        "black_large_square_button": "black_square_button",
        "black_right_pointing_double_triangle_with_vertical_bar": "next_track",
        "black_square": "black_large_square",
        "bow": "person_bowing",
        "cop": "police_officer",
        "cool-glasses": "smiling_face_with_sunglasses",
        "doctor": "health_worker",
        "face_palm": "man_facepalming",
        "drum_with_drumsticks": "drum",
        "face_with_cowboy_hat": "cowboy_hat_face",
        "face_with_finger_covering_closed_lips": "shushing_face",
        "grinning_face_with_star_eyes": "star-struck",
        "juggling": "juggling_person",
        "knife_fork_plate": "plate_with_cutlery",
        "ladybug": "lady_beetle",
        "large_orange_square": "orange_square",
        "lightning": "high_voltage",
        "monkey_eyes": "see_no_evil",
        "mostly_sunny": "sun_behind_small_cloud",
        "muscle": "flexed_biceps",
        "octagonal_sign": "stop_sign",
        "partly_sunny_rain": "sun_behind_rain_cloud",
        "rain_cloud": "cloud_with_rain",
        "rolled_up_newspaper": "rolled-up_newspaper",
        "santa": "Santa_Claus",
        "scooter": "kick_scooter",
        "shocked": "flushed",
        "shrug": "person_shrugging",
        "smiling_face_with_3_hearts": "smiling_face_with_hearts",
        "smiling_face_with_smiling_eyes_and_hand_covering_mouth": "face_with_hand_over_mouth",
        "snow_cloud": "cloud_with_snow",
        "spock-hand": "vulcan_salute",
        "sun_small_cloud": "sun_behind_small_cloud",
        # animals
        "lion_face": "lion",
        "zebra_face": "zebra",
        # flags
        "flag-at": "Australia",
        "flag-au": "Austria",
        "flag-br": "Brazil",
        "flag-england": "England",
        "flag-ch": "Switzerland",
        "flag-cn": "China",
        "flag-co": "Colombia",
        "flag-de": "Germany",
        "flag-gg": "Guernsey",
        "flag-ie": "Ireland",
        "flag-nl": "Netherlands",
        "flag-nr": "Nauru",
        "flag-nz": "New_Zealand",
        "flag-pl": "Poland",
        "flag-pt": "Portugal",
        "flag-tr": "Turkey",
        "flag-ru": "Russia",
        "flag-st": "São_Tomé_&_Príncipe",
        "flag-um": "United_States",
        "flag-us": "United_States",
        "flag-vc": "st_vincent_grenadines",
        # persons
        "female-": "woman_",
        "female_": "woman_",
        "male-": "man_",
        "male_": "man_",
        "man-": "man_",
        "woman-": "woman_",
        "man_lifting-weights": "person_lifting_weights",
        "weight_lifter": "person_lifting_weights",
        "man_and_woman_holding_hands": "couple",
        "man_construction-worker": "man_construction_worker",
        "woman_construction-worker": "woman_construction_worker",
        "man_doctor": "man_health_worker",
        "woman_doctor": "woman_health_worker",
        "woman_gesturing-no": "woman_gesturing_NO",
        "man_gesturing-no": "man_gesturing_NO",
        "man_mountain-biking": "man_mountain_biking",
        "woman_mountain-biking": "woman_mountain_biking",
        "man_police-officer": "man_police_officer",
        "woman_police-officer": "woman_police_officer",
        "man_raising-hand": "man_raising_hand",
        "woman_raising-hand": "woman_raising_hand",
        "man_sign": "male_sign",
        "woman_sign": "female_sign",
        "person_doing_cartwheel": "person_cartwheeling",
        "man_doing_cartwheel": "man_cartwheeling",
        "woman_doing_cartwheel": "woman_cartwheeling",
        "man_tipping-hand": "man_tipping_hand",
        "woman_tipping-hand": "woman_tipping_hand",
        "man_with-bunny-ears-partying": "men_with_bunny_ears",
        "woman_with-bunny-ears-partying": "women_with_bunny_ears",
        "woman_gesturing-ok": "woman_gesturing_OK",
        "man_gesturing-ok": "man_gesturing_OK",
        "raising_hand": "man_raising_hand",
        "bicyclist": "person_biking",
        "man_in_business_suit_levitating": "person_in_suit_levitating",
        "older_man": "old_man",
        "older_woman": "old_woman",
        "runner": "person_running",
        "surfer": "person_surfing",
        "two_men_holding_hands": "men_holding_hands",
        "two_women_holding_hands": "women_holding_hands",
        "water_polo": "person_playing_water_polo",
        # hands
        "-1": "thumbs_down",
        "+1": "thumbs_up",
        "clap_": "clapping_hands_",
        "hand_with_index_and_middle_fingers_crossed": "crossed_fingers",
        "i_love_you_hand_sign": "love-you_gesture",
        "index_pointing_up_2": "index_pointing_up",
        "italian-hand": "pinched_fingers",
        "ok_hand": "OK_hand",
        "point_left": "backhand_index_pointing_left",
        "point_right": "backhand_index_pointing_right",
        "point_up_2": "backhand_index_pointing_up",
        "point_up": "index_pointing_up",
        "pray": "folded_hands",
        "raised_hand_with_fingers_splayed": "hand_with_fingers_splayed",
        "raised_hands": "raising_hands",
        "facepunch": "oncoming_fist",
        "the_horns": "sign_of_the_horns",
        "thumbsup": "thumbs_up",
        "v_": "victory_hand_",
        "wave": "waving_hand",
        # families
        "man_man_girl-girl": "family_man_man_girl_girl",
        "man_man_girl-boy": "family_man_man_girl_boy",
        "man_man_boy-boy": "family_man_man_boy_boy",
        "woman_woman_girl-girl": "family_woman_woman_girl_girl",
        "woman_woman_girl-boy": "family_woman_woman_girl_boy",
        "woman_woman_boy-boy": "family_woman_woman_boy_boy",
        "man_woman_girl-girl": "family_man_woman_girl_girl",
        "man_woman_girl-boy": "family_man_woman_girl_boy",
        "man_woman_boy-boy": "family_man_woman_boy_boy",
        "woman_boy-boy": "family_woman_boy_boy",
        "man_boy-boy": "family_man_boy_boy",
        "man_woman_girl": "family_man_woman_girl",
        "man_woman_boy": "family_man_woman_boy",
        "man_man_girl": "family_man_man_girl",
        "man_man_boy": "family_man_man_boy",
        "woman_woman_girl": "family_woman_woman_girl",
        "woman_woman_boy": "family_woman_woman_boy",
        "woman_girl-boy": "family_woman_girl_boy",
        "man_girl-boy": "family_man_girl_boy",
        "woman_girl-girl": "family_woman_girl_girl",
        "man_girl-girl": "family_man_girl_girl",
        "man_boy": "family_man_boy",
        "woman_boy": "family_woman_boy",
        "man_girl": "family_man_girl",
        "woman_girl": "family_woman_girl",
        # medals
        "medal": "sports_medal",
        "first_place_medal": "1st_place_medal",
        "second_place_medal": "2nd_place_medal",
        "third_place_medal": "3rd_place_medal",
        # TODO extend this or find a nicer/automatic solution
    }

    def __init__(self):
        self._read_user_file()
        self._read_channel_file()

    def _read_user_file(self):
        user_file = open("data/users.txt", "r", encoding="utf-8")
        lines = user_file.readlines()
        for line in lines[2:]:
            parts = line.split(" ")
            parts = [i for i in parts if i != ""]
            self.user_map[parts[1]] = self.to_pretty_user(parts[0])

    def _read_channel_file(self):
        user_file = open("data/channels.txt", "r", encoding="utf-8")
        lines = user_file.readlines()
        for line in lines[1:]:
            line = line.replace("🔒 ", "🔒").strip()
            parts = line.split(" ")
            self.channel_map[parts[0]] = (ChannelType(parts[-1][0]), parts[-1][1:])

    def replace_names(self, slack_data: SlackData):
        for message in slack_data.messages:
            message.user = self.get_user_name(message.user)
            for reply in message.replies:
                reply.user = self.get_user_name(reply.user)

    def get_user_name(self, user_id: str):
        if user_id in self.user_map:
            return self.user_map[user_id]
        else:
            return user_id

    def to_pretty_user(self, user: str) -> str:
        if "." in user:
            pretty_user_name = user.replace(".", " ")
            return pretty_user_name.title()
        else:
            return user

    def replace_emoji_name(self, emoji_name: str):
        if emoji_name == "hand" or emoji_name.startswith("hand::"):
            emoji_name = "raised_hand" + emoji_name[5:]
        for skin_tone in self.emoji_skin_tones.items():
            emoji_name = emoji_name.replace(f"::skin-tone-{skin_tone[0]}", skin_tone[1])
        for emoji in self.emoji_name_start_slack_to_lib.items():
            if emoji_name.startswith(emoji[0]):
                emoji_name = emoji_name.replace(emoji[0], emoji[1])
        return emoji_name

    def replace_emoji_name_with_skin_tone(self, emoji_text, skin_tone: int):
        return emoji_text + self.emoji_skin_tones[skin_tone]
