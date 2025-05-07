# pip install openaustralia
from openaustralia import OpenAustralia

oa = OpenAustralia("Ewi4hND52eCqBFGFsGCmjqoS")

pauline_hanson_list = oa.get_senators(date=None, party=None, state=None, search="Pauline")
print(pauline_hanson_list)
pauline_hanson_id = pauline_hanson_list[0]["person_id"]

#[{'member_id': '100857', 'house': '2', 'first_name': 'Pauline', 'last_name': 'Hanson', 'constituency': 'Queensland', 'party': "Pauline Hanson's One Nation Party", 'entered_house': '2016-07-01', 'left_house': '9999-12-31', 'entered_reason': 'general_election', 'left_reason': 'still_in_office', 'person_id': '10280', 'title': '', 'lastupdate': '2016-08-30 08:46:35', 'full_name': 'Pauline Hanson', 'name': 'Pauline Hanson', 'image': '/images/mpsL/10280.jpg'}]

comments_about_housing = oa.get_comments(date=None, search="housing", user_id=None, pid=pauline_hanson_id, page=None, num=2)
print(comments_about_housing)

# {'comments': [{'comment_id': '1366', 'user_id': '3359', 'epobject_id': '625976', 'body': 'Could I ask how much will also be used for Housing in the Disability Sector? Thanking you Philip Hodges', 'posted': '2018-03-23 13:57:05', 'major': '101', 'gid': 'uk.org.publicwhip/lords/2018-03-22.25.4', 'firstname': 'Philip', 'lastname': 'Hodges', 'url': '/senate/?gid=2018-03-22.25.4#c1366'}, {'comment_id': '1362', 'user_id': '2509', 'epobject_id': '625608', 'body': 'SUsan Lamb is correct over the total mess that LNOP has made of housing. I recall a DLP campaign volumnteer finding and phoprtographiong whole blocks of Housing COmmission units that had nebver been occupied. \r\n\r\nHowever SHE IS WRONG WHEN SHE SAYS SHE HAS A PLAN. "onsultation is normally a way of avoiding  making  decision. \r\n\r\nSusan has now had enough time to have done her consultation She needs to now state what she and her fellow ALP MP\'s will do to represent the residents of Longman.\r\n\r\nShe is improving though and seems to be thinking of areas 44-60KM from City centre rather than just worrying about the inner city residents.  \r\n\r\nI for one am not convinced that removing negative gearing would be beneficial nor for that matter am I convinced that retaining it is beneficial.', 'posted': '2018-03-02 18:59:18', 'major': '1', 'gid': 'uk.org.publicwhip/debate/2018-03-01.13.1', 'firstname': 'Andrew', 'lastname': 'JACKSON', 'url': '/debate/?id=2018-03-01.13.1#c1362'}], 'search': 'housing'}
