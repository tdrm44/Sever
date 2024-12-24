#!/usr/bin/env python

# This is a simple web server for a training record application.
# It's your job to extend it by adding the backend functionality to support
# recording training in an SQL database. You will also need to support
# user access/session control. You should only need to extend this file.
# The client side code (html, javascript and css) is complete and does not
# require editing or detailed understanding, it serves only as a
# debugging/development aid.

# import the various libraries needed
import http.cookies as Cookie   # some cookie handling support
from http.server import BaseHTTPRequestHandler, HTTPServer # the heavy lifting of the web server
import urllib # some url parsing support
import json   # support for json encoding
import sys    # needed for agument handling
import time   # time support

import base64 # some encoding support
import sqlite3 # sql database
import random # generate random numbers
import time # needed to record when stuff happened
import datetime

def random_digits(n):
    """This function provides a random integer
        with the specfied number of digits and no leading zeros."""
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return random.randint(range_start, range_end)

# The following three functions issue SQL queries to the database.

def do_database_execute(op):
    """Execute an sqlite3 SQL query to database.db that does not expect a response."""
    print(op)
    try:
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        cursor.execute(op)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def do_database_fetchone(op):
    """Execute an sqlite3 SQL query to database.db that
        expects to extract a single row result. Note, it may be a null result."""
    print(op)
    try:
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        cursor.execute(op)
        result = cursor.fetchone()
        print(result)
        db.close()
        return result
    except Exception as e:
        print(e)
        return None

def do_database_fetchall(op):
    """Execute an sqlite3 SQL query to database.db that
        expects to extract a multi-row result. Note, it may be a null result."""
    print(op)
    try:
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        cursor.execute(op)
        result = cursor.fetchall()
        print(result)
        db.close()
        return result
    except Exception as e:
        print(e)
        return None

# The following build_ functions return the responses that the front end client understands.
# You can return a list of these.

def build_response_message(code, text):
    """This function builds a message response that displays a message
       to the user on the web page. It also returns an error code."""
    return {"type":"message", "code":code, "text":text}

def build_response_skill(id, name, gained, trainer, state):
    """This function builds a summary response that contains one summary table entry."""
    return {"type":"skill", "id":id, "name":name, "gained":gained, "trainer":trainer, "state":state}

def build_response_class(id, name, trainer, when, notes, size, max, action):
    """This function builds an activity response that
        contains the id and name of an activity type,"""
    return {"type":"class", "id":id, "name":name, "trainer":trainer, "when":when, "notes":notes, "size":size, "max":max, "action":action}

def build_response_attendee(id, name, action):
    """This function builds an activity response that
        contains the id and name of an activity type,"""
    return {"type":"attendee", "id":id, "name":name, "action":action}

def build_response_redirect(where):
    """This function builds the page redirection response
       It indicates which page the client should fetch.
       If this action is used, it should be the only response provided."""
    return {"type":"redirect", "where":where}

# The following handle_..._request functions
# are invoked by the corresponding /action?command=.. request
def handle_login_request(iuser, imagic, content):
    """A user has supplied a username and password. Check if these are
       valid and if so, create a suitable session record in the database
       with a random magic identifier that is returned.
       Return the username, magic identifier and the response action set."""

    response = []
    ## Add code here

    # check if username/password is string type
    try:
        username = str(content["username"])
        password = str(content["password"])
    except ValueError:
        response.append(build_response_message(200, "Invalid username or password"))
        return [iuser, imagic, response]

    # detect incorrect username/ps
    if not username:
        response.append(build_response_message(101, "Missing username"))
    elif not password:
        response.append(build_response_message(102, "Missing password"))
    elif username.find("'") != -1:
        response.append(build_response_message(201, "Bad username input"))
    elif password.find("'") != -1:
        response.append(build_response_message(202, "Bad password input"))
    else:
        # fetch username and password
        user = do_database_fetchone(f"""SELECT userid
                                        FROM users 
                                        WHERE username = '{username}' 
                                        AND password = '{password}'""")

        if user is None:
            response.append(build_response_message(203, "The username and password does not match"))
        else:
            userid = user[0]
            iuser = username
            imagic = random_digits(12)

            # remove the existing sessions of the user
            do_database_execute(f"DELETE FROM session WHERE userid = {userid};")
            # create a new session of the user
            do_database_execute(f"INSERT INTO session (userid, magic) VALUES ({userid}, {imagic});")

            # append msg and redirect response
            response.append(build_response_message(0, "Successfully logged in"))
            response.append(build_response_redirect("/index.html"))

    return [iuser, imagic, response]

def handle_logout_request(iuser, imagic, parameters):
    """This code handles the selection of the logout button.
       You will need to ensure the end of the session is recorded in the database
       And that the session magic is revoked."""

    response = []
    ## Add code here
    # check if it's not an expected iuser/imagic
    if "'" in iuser or not imagic.isdigit():
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]

    # login_session
    session = do_database_fetchone(f"""
                                   SELECT session.userid 
                                   FROM session 
                                   JOIN users ON session.userid = users.userid
                                   WHERE username = '{iuser}' AND magic = {imagic};""")

    # if no login session, redirect to login page
    if session is None:
        response.append(build_response_redirect("/login.html"))
    else:
        do_database_execute(f"DELETE FROM session WHERE userid = {session[0]};")
        response.append(build_response_redirect("/logout.html"))
    iuser = "!"

    return [iuser, imagic, response]

def handle_get_my_skills_request(iuser, imagic):
    """This code handles a request for a list of a users skills.
       You must return a value for all vehicle types, even when it's zero."""

    response = []
    ## Add code here
    ### get id&magic token --> use these to find skills of this user, evry skils
    # check credential
    if "'" in iuser or not imagic.isdigit():
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]
    # login_session
    session = do_database_fetchone(f"""
                                   SELECT session.userid 
                                   FROM session 
                                   JOIN users ON session.userid = users.userid
                                   WHERE username = '{iuser}' AND magic = {imagic};""")
    # if user not logging in, redirect to login page
    if not session:
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]

    userid = session[0]

    # fetch trainers data
    trainers = do_database_fetchall(f"SELECT skillid FROM trainer WHERE trainerid = {userid}")

    trainer_skillids = "(" + ",".join(str(trainer[0]) for trainer in trainers) + ")" if trainers else "()"

    # fetch not fail data
    notfails = do_database_fetchall(f"""
                                    SELECT skillid
                                    FROM attendee
                                    JOIN class ON attendee.classid = class.classid
                                    WHERE attendee.userid = {userid} AND attendee.status IN (0, 1)
                                        AND strftime('%s', DATETIME('NOW')) > class.start
                                    GROUP BY skillid;
                                    """)

    notfail_skillids = "(" + ",".join(str(notfail[0]) for notfail in notfails) + ")" if notfails else "()"

    # to sort skills, case by state
    skills = do_database_fetchall(f"""SELECT
                                    skill.skillid,
                                    skill.name,
                                    users.fullname,
                                    class.start AS gained,
                                    CASE
                                        WHEN skill.skillid IN {trainer_skillids} THEN 'trainer'
                                        ELSE 'passed'
                                    END state
                                    FROM skill
                                    LEFT JOIN class ON skill.skillid = class.skillid
                                    LEFT JOIN attendee ON class.classid = attendee.classid
                                    LEFT JOIN users ON class.trainerid = users.userid
                                    WHERE (attendee.userid = {userid} AND attendee.status = 1)

                                    UNION

                                    SELECT
                                    skill.skillid,
                                    skill.name,
                                    users.fullname AS trainername,
                                    class.start AS gained,
                                    CASE
                                        WHEN strftime('%s', DATETIME('NOW')) > class.start THEN 'pending'
                                        ELSE 'scheduled'
                                    END state
                                    FROM skill
                                    JOIN class ON skill.skillid = class.skillid
                                    JOIN attendee ON class.classid = attendee.classid
                                    JOIN users ON class.trainerid = users.userid
                                    WHERE attendee.userid = {userid} AND attendee.status = 0 
                                        AND ((strftime('%s', DATETIME('NOW')) > class.start) 
                                                OR ((strftime('%s', DATETIME('NOW')) < class.start) 
                                                    AND skill.skillid NOT IN 
                                                        (SELECT c.skillid FROM class c 
                                                        JOIN attendee a ON a.classid = c.classid 
                                                        WHERE a.userid = {userid} AND a.status = 3)))

                                    UNION

                                    SELECT
                                    skill.skillid,
                                    skill.name,
                                    users.fullname AS trainername,
                                    class.start AS gained,
                                    'failed' AS state
                                    FROM skill
                                    JOIN class ON skill.skillid = class.skillid
                                    JOIN attendee ON class.classid = attendee.classid
                                    JOIN users ON class.trainerid = users.userid
                                    WHERE attendee.userid = {userid} AND attendee.status = 2 
                                        AND skill.skillid NOT IN {notfail_skillids}
                                        AND skill.skillid NOT IN {trainer_skillids};""")
    # loop to return the responses
    for skill in skills:
        skillid, skillname, trainername, gained, state = skill[:5]

        response.append(build_response_skill(skillid, skillname, gained, trainername, state))
        response.append(build_response_message(0, "Skill lists provided"))

    return [iuser, imagic, response]

def handle_get_upcoming_request(iuser, imagic):
    """This code handles a request for the details of a class."""

    response = []
    ## Add code here
    # check credential
    if "'" in iuser or not imagic.isdigit():
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]
    # login_session
    session = do_database_fetchone(f"""
                                   SELECT session.userid 
                                   FROM session 
                                   JOIN users ON session.userid = users.userid
                                   WHERE username = '{iuser}' AND magic = {imagic};""")
    # if user not logging in, redirect to login page
    if not session:
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]

    userid = session[0]

    # class data; case sorting by action
    classes = do_database_fetchall(f"""SELECT
                                    class.classid,
                                    skill.name,
                                    users.fullname,
                                    class.note,
                                    class.start,
                                    (SELECT COUNT (*) from attendee WHERE attendee.classid = class.classid AND attendee.status = 0) AS size,
                                    class.max,
                                    CASE
                                        WHEN class.max = 0
                                                OR EXISTS (SELECT 1 FROM attendee WHERE attendee.classid = class.classid AND attendee.status = 4 and attendee.userid = {userid}) THEN 'cancelled' 
                                        WHEN class.trainerid = {userid} THEN 'edit'
                                        WHEN EXISTS (SELECT 1 FROM attendee 
                                                    WHERE attendee.classid = class.classid AND attendee.status = 0 AND attendee.userid = {userid}) THEN 'leave'
                                        WHEN NOT EXISTS (SELECT 1 FROM attendee
                                                    WHERE attendee.classid = class.classid AND attendee.status IN (0,4) AND attendee.userid = {userid}
                                                UNION 
                                                    SELECT 1 FROM attendee JOIN class c ON c.classid = attendee.classid 
                                                    WHERE c.skillid = class.skillid AND attendee.status IN (0,1) AND attendee.userid = {userid}) THEN 'join'
                                        ELSE 'unavailable'
                                    END action
                                    FROM class
                                    JOIN skill ON skill.skillid = class.skillid
                                    JOIN users ON users.userid = class.trainerid
                                    WHERE strftime('%s', DATETIME('NOW')) < class.start
                                    ORDER BY class.start ASC;""")

    # for upcoming class in the past
    if not classes:
        response.append(build_response_message(0, "No upcoming class available"))
        return [iuser, imagic, response]

    # loop to return the class response
    for _class in classes:
        classid, skillname, trainername, note, when, size, _max, action = _class[:8]

        response.append(
            build_response_class(
                classid, skillname, trainername, when, note, size, _max, action
                )
        )
        response.append(build_response_message(0, "Upcoming classes provided"))

    return [iuser, imagic, response]

def handle_get_class_detail_request(iuser, imagic, content):
    """This code handles a request for a list of upcoming classes."""
    response = []

    ## Add code here
    # check if any injection from iuser(username) and imagic
    if "'" in iuser or not imagic.isdigit():
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]
    # login_session
    session = do_database_fetchone(f"""
                                   SELECT session.userid 
                                   FROM session 
                                   JOIN users ON session.userid = users.userid
                                   WHERE username = '{iuser}' AND magic = {imagic};""")
    # if user not logging in, redirect to login page
    if not session:
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]

    userid = session[0]
    classid = content["id"]

    # check if classid is int
    try:
        classid = int(classid)
    except ValueError:
        response.append(build_response_message(240, "Bad classid"))
        return [iuser, imagic, response]

    # class data
    _class = do_database_fetchone(f"""SELECT
                                    skill.name, 
                                    class.trainerid, 
                                    users.fullname, 
                                    class.note, 
                                    class.start, 
                                    class.max
                                    FROM class
                                    JOIN skill ON class.skillid = skill.skillid
                                    JOIN users ON class.trainerid = users.userid
                                    WHERE class.classid = {classid};""")

    if not _class:
        response.append(build_response_message(241, "Not existing class"))
        return [iuser, imagic, response]

    name, trainerid, trainer, note, when, _max = _class

    # check if not trainerid
    if trainerid != userid:
        response.append(build_response_message(242, "You aren't the trainer of this class"))
        return [iuser, imagic, response]

    # attendee data
    attendees = do_database_fetchall(f"""
                                     SELECT *
                                     FROM attendee
                                     JOIN users ON attendee.userid = users.userid
                                     WHERE attendee.classid = {classid}
                                        AND attendee.status NOT IN (3, 4);""")
    # check size
    size = len(attendees)

    # get enrolled attendee data
    enrolled_attendee = do_database_fetchall(f"""
                                            SELECT
                                            attendeeid,
                                            fullname,
                                            status
                                            FROM attendee
                                            JOIN users ON users.userid = attendee.userid 
                                            WHERE attendeeid IN (SELECT MAX(attendeeid)
                                            FROM attendee WHERE classid = {classid}
                                            GROUP BY userid);""")

    # check time; now and starting time of class
    now = datetime.datetime.now()
    start = datetime.datetime.fromtimestamp(int(when))

    # loop to state the attendees' status; and append attendee response
    for attendeeid, fullname, status in enrolled_attendee:
        if status == 0:
            if now < start:
                state = "remove"
            else: state = "update"
        if status == 1:
            state = "passed"
        if status == 2:
            state = "failed"
        if status in (3, 4):
            state = "cancelled"

        response.append(build_response_attendee(attendeeid, fullname, state))

    # check if max != 0 then class is cancelled
    if not _max:
        response.append(
            build_response_class(
                classid, name, trainer, when, note, size, _max, "cancelled"
            )
        )
        return [iuser, imagic, response]

    # check if class hasn't started yet, then able to cancel
    if now < start:
        response.append(
            build_response_class(classid, name, trainer, when, note, size, _max, "cancel"
                                 )
        )
    else: # class has already started, then unable to cancel but what behaviour is expected??
        response.append(build_response_class(classid, name, trainer, when, note, size, _max, " "))

    return [iuser, imagic, response]

def handle_join_class_request(iuser, imagic, content):
    """This code handles a request by a user to join a class."""
    response = []

    ## Add code here
    # content = {”id”: classid}
    # check credential
    # check if any injection from iuser(username) and imagic
    if "'" in iuser or not imagic.isdigit():
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]
    # login_session
    session = do_database_fetchone(f"""
                                   SELECT session.userid 
                                   FROM session 
                                   JOIN users ON session.userid = users.userid
                                   WHERE username = '{iuser}' AND magic = {imagic};""")
    # if user not logging in, redirect to login page
    if not session:
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]

    if isinstance(content, dict) is False:
        response.append(build_response_message(150, "Missing parameter: No content input"))
        return [iuser, imagic, response]

    if content.get("id") is None:
        response.append(build_response_message(151, "Missing parameter: No classid"))
        return [iuser, imagic, response]

    userid = session[0]
    classid = content["id"]

    # check if classid is int type
    try:
        classid = int(classid)
    except ValueError:
        response.append(build_response_message(250, "Bad classid"))
        return [iuser, imagic, response]

    # get class data from
    _class = do_database_fetchone(f"""
                                    SELECT 
                                    class.classid, 
                                    class.skillid,
                                    skill.name, 
                                    class.trainerid, 
                                    users.fullname, 
                                    class.note, 
                                    class.start, 
                                    class.max
                                    FROM class
                                    JOIN skill ON class.skillid = skill.skillid
                                    JOIN users ON class.trainerid = users.userid
                                    WHERE classid = {classid};""")

    # check if class is existing
    if not _class:
        response.append(build_response_message(251, "Not existing class"))
        return [iuser, imagic, response]

    _, skillid, _, _, _, _, when, _max = _class

    # check cond. that unable to join
    try:
        # get attendee of the class
        attendees = do_database_fetchone(f"""SELECT COUNT(*)
                                FROM attendee WHERE classid = {classid}
                                AND status NOT IN (3, 4);""")

        tot_attendee = attendees[0]
        if tot_attendee >= _max:
            raise ValueError('252')

        # check time
        now = int(datetime.datetime.now().timestamp())
        start = int(when)
        if start < now:
            raise ValueError('253')

        # check if attendee got removed
        isremoved = do_database_fetchone(f"""SELECT *
                                            FROM attendee WHERE userid = {userid}
                                            AND classid = {classid} AND status = 4;""")
        if isremoved:
            raise ValueError('254')

        # check if attendee got passed or being enrolled
        ispassed_or_enrolled = do_database_fetchone(f"""SELECT *
                                            FROM attendee
                                            JOIN class ON class.classid = attendee.classid
                                            WHERE userid = {userid} AND skillid = {skillid}
                                            AND status IN (0, 1);""")
        if ispassed_or_enrolled:
            raise ValueError('255')

    except ValueError as va_er:
        if va_er.args[0] == '252':
            response.append(
                build_response_message(252, "Unable to join; Class full"
                                       )
            )
        if va_er.args[0] == '253':
            response.append(
                build_response_message(253, "Unable to join; Class already started"
                                       )
            )
        if va_er.args[0] == '254':
            response.append(
                build_response_message(254, "Unable to join; Got removed from class"
                                       )
            )
        if va_er.args[0] == '255':
            response.append(
                build_response_message(255, "Unable to join; Already passed/enrolled"
                                       )
            )
        return [iuser, imagic, response]

    # join class by inserting into attendee db
    do_database_execute(f"""INSERT INTO attendee (userid, classid, status)
                            VALUES ({userid}, {classid}, 0);""")

    join_classes = do_database_fetchall(f"""SELECT
                                    class.classid,
                                    skill.name,
                                    users.fullname,
                                    class.note,
                                    class.start,
                                    (SELECT COUNT (*) from attendee WHERE attendee.classid = class.classid AND attendee.status = 0) AS size,
                                    class.max,
                                    CASE
                                        WHEN EXISTS (SELECT 1 FROM attendee WHERE attendee.classid = class.classid
                                                    AND attendee.status = 4 AND attendee.userid = {userid}) THEN 'cancelled'
                                        WHEN EXISTS (SELECT 1 FROM attendee WHERE attendee.classid = class.classid
                                                    AND attendee.status = 0 AND attendee.userid = {userid}) THEN 'leave'
                                        ELSE 'unavailable'
                                    END action    
                                    FROM class
                                    JOIN skill ON skill.skillid = class.skillid
                                    JOIN users ON users.userid = class.trainerid
                                    WHERE strftime('%s', DATETIME('NOW')) < class.start
                                        AND class.skillid = {skillid} AND class.max > 0;""")

    # loop to return the class response
    for classid, skillname, trainername, note, when, size, _max, action in join_classes:
        response.append(
            build_response_class(
                classid, skillname, trainername, when, note, size, _max, action
                )
        )
        response.append(build_response_message(0, "Successfully joined class"))

    return [iuser, imagic, response]

def handle_leave_class_request(iuser, imagic, content):
    """This code handles a request by a user to leave a class."""
    response = []

    ## Add code here
    # check credential
    # check if any injection from iuser(username) and imagic
    if "'" in iuser or not imagic.isdigit():
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]
    # login_session
    session = do_database_fetchone(f"""
                                   SELECT session.userid 
                                   FROM session 
                                   JOIN users ON session.userid = users.userid
                                   WHERE username = '{iuser}' AND magic = {imagic};""")
    # if user not logging in, redirect to login page
    if not session:
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]

    if isinstance(content, dict) is False:
        response.append(build_response_message(160, "Missing parameter: No content input"))
        return [iuser, imagic, response]

    if content.get("id") is None:
        response.append(build_response_message(161, "Missing parameter: No classid"))
        return [iuser, imagic, response]

    userid = session[0]
    classid = content["id"]

    # check if classid is int
    try:
        classid = int(classid)
    except ValueError:
        response.append(build_response_message(260, "Bad classid"))
        return [iuser, imagic, response]

    # get class data
    _class = do_database_fetchone(f"""
                                  SELECT
                                   class.classid, 
                                   class.skillid,
                                   skill.name, 
                                   class.trainerid, 
                                   users.fullname, 
                                   class.note, 
                                   class.start, 
                                   class.max
                                  FROM class
                                  JOIN skill ON class.skillid = skill.skillid
                                  JOIN users ON class.trainerid = users.userid
                                  WHERE classid = {classid};""")

    # check if class is existing
    if not _class:
        response.append(build_response_message(261, "Not existing class"))
        return [iuser, imagic, response]

    skillid = _class[1]
    when = _class[6]

    # check if class already started
    now = int(datetime.datetime.now().timestamp())
    start = int(when)
    if now > start:
        response.append(build_response_message(262, "Too late to leave.."))
        return [iuser, imagic, response]

    # get attendee data from (use fetchone)
    attendee = do_database_fetchone(f"""
                                    SELECT *
                                    FROM attendee
                                    WHERE classid = {classid} AND userid = {userid} AND status = 0;
                                    """)
    # check if user is an attendee
    if not attendee:
        response.append(build_response_message(263, "You're not an attendee of the class"))
        return [iuser, imagic, response]

    # UPDATE attendee SET status = 3 WHERE classid = {classid} AND userid = {userid}
    do_database_execute(f"""UPDATE attendee
                            SET status = 3 WHERE classid = {classid} AND userid = {userid};""")

    # check if same-skill classes are crashing or not
    leave_classes = do_database_fetchall(f"""SELECT
                                    class.classid,
                                    skill.name,
                                    users.fullname,
                                    class.note,
                                    class.start,
                                    (SELECT COUNT (*) from attendee WHERE attendee.classid = class.classid AND attendee.status = 0) AS size,
                                    class.max,
                                    CASE
                                        WHEN EXISTS (SELECT 1 FROM attendee WHERE attendee.classid = class.classid
                                                        AND attendee.status = 4 AND attendee.userid = {userid}) THEN 'cancelled'
                                        WHEN NOT EXISTS (SELECT 1 FROM attendee WHERE attendee.classid = class.classid
                                                        AND attendee.status = 4 AND attendee.userid = {userid}) THEN 'join'
                                        ELSE 'unavailable'
                                    END    
                                   FROM class
                                   JOIN skill ON skill.skillid = class.skillid
                                   JOIN users ON users.userid = class.trainerid
                                   WHERE strftime('%s', DATETIME('NOW')) < class.start AND class.skillid = {skillid} AND class.max > 0
                                   """)

    # loop to return the class response
    for classid, skillname, trainername, note, when, size, _max, action in leave_classes:

        response.append(
            build_response_class(
                classid, skillname, trainername, when, note, size, _max, action
                )
        )
        response.append(build_response_message(0, "Successfully left class"))

    return [iuser, imagic, response]

def handle_cancel_class_request(iuser, imagic, content):
    """This code handles a request to cancel an entire class."""

    response = []
    ## Add code here
    # check credential
    # check if any injection from iuser(username) and imagic
    if "'" in iuser or not imagic.isdigit():
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]
    # login_session
    session = do_database_fetchone(f"""
                                   SELECT session.userid 
                                   FROM session 
                                   JOIN users ON session.userid = users.userid
                                   WHERE username = '{iuser}' AND magic = {imagic};""")
    # if user not logging in, redirect to login page
    if not session:
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]

    if isinstance(content, dict) is False:
        response.append(build_response_message(170, "Missing parameter: No content input"))
        return [iuser, imagic, response]

    if content.get("id") is None:
        response.append(build_response_message(171, "Missing parameter: No classid"))
        return [iuser, imagic, response]

    userid = session[0]
    classid = content["id"]

    # check if classid is int type
    try:
        classid = int(classid)
    except ValueError:
        response.append(build_response_message(270, "Bad classid"))
        return [iuser, imagic, response]

    # get class data from
    _class = do_database_fetchone(f"""
                                  SELECT 
                                   class.classid, 
                                   class.skillid,
                                   skill.name, 
                                   class.trainerid, 
                                   users.fullname, 
                                   class.note, 
                                   class.start, 
                                   class.max
                                  FROM class
                                  JOIN skill ON class.skillid = skill.skillid
                                  JOIN users ON class.trainerid = users.userid
                                  WHERE classid = {classid};""")

    # check if class is existing
    if not _class:
        response.append(build_response_message(271, "Not existing class"))
        return [iuser, imagic, response]

    _, _, skillname, trainerid, trainername, note, when, _ = _class

    # check if trainer; if trainer then able to cancel
    if userid != trainerid:
        response.append(build_response_message(272, "You aren't the trainer of this class"))
        return [iuser, imagic, response]

    #check if class already started
    now = int(datetime.datetime.now().timestamp())
    _when = int(when)
    if now > _when:
        response.append(build_response_message(273, "Too late to cancel.."))
        return [iuser, imagic, response]

    # UPDATE class SET max = 0 WHERE classid = content["id"]
    do_database_execute(f"UPDATE class SET max = 0 WHERE classid = {classid};")

    # get enrolled attendee
    enrolled_attendee = do_database_fetchall(f"""
                                            SELECT
                                            attendeeid,
                                            fullname
                                            FROM attendee
                                            JOIN users ON users.userid = attendee.userid 
                                            WHERE classid = {classid} AND status = 0;""")

    # UPDATE attendee
    do_database_execute(f"""UPDATE attendee
                            SET status = 3 WHERE classid = {classid} AND status = 0;""")

    # class response
    response.append(
        build_response_class(
            classid, skillname, trainername, when, note, 0, 0, "cancelled"
            )
    )
    # attendee response
    for attendeeid, fullname in enrolled_attendee:
        response.append(build_response_attendee(attendeeid, fullname, "cancelled"))

    response.append(build_response_message(0, "Successfully canceled class"))
    return [iuser, imagic, response]

def handle_update_attendee_request(iuser, imagic, content):
    """This code handles a request to cancel a user attendance at a class by a trainer"""

    response = []
    ## Add code here
    # check credential
    # check if any injection from iuser(username) and imagic
    if "'" in iuser or not imagic.isdigit():
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]
    # login_session
    session = do_database_fetchone(f"""
                                   SELECT session.userid 
                                   FROM session 
                                   JOIN users ON session.userid = users.userid
                                   WHERE username = '{iuser}' AND magic = {imagic};""")
    # if user not logging in, redirect to login page
    if not session:
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]

    userid = session[0]
    attendeeid = content["id"]
    state = content["state"]

    # check if type of attendeeid is int
    try:
        attendeeid = int(attendeeid)
    except ValueError:
        response.append(build_response_message(280, "Bad attendeeid"))
        return [iuser, imagic, response]

    # get attendee data
    attendee = do_database_fetchone(f"""
                                    SELECT fullname, status
                                    FROM attendee
                                    JOIN users ON users.userid = attendee.userid
                                    WHERE attendeeid = {attendeeid};""")
    # check if given id is an attendee
    if not attendee:
        response.append(build_response_message(281, "This person isn't enrolled to the class"))
        return [iuser, imagic, response]

    # get class data from (fetchone)
    _class = do_database_fetchone(f"""SELECT
                                    class.classid, 
                                    skill.name, 
                                    class.trainerid, 
                                    users.fullname, 
                                    class.note, 
                                    class.start, 
                                    class.max,
                                    attendee.status,
                                    u.fullname AS attendeename
                                    FROM class
                                    JOIN users ON class.trainerid = users.userid
                                    JOIN skill ON class.skillid = skill.skillid
                                    JOIN attendee ON class.classid = attendee.classid
                                    JOIN users u ON u.userid = attendee.userid 
                                    WHERE attendeeid = {attendeeid};""")

    if not _class:
        response.append(build_response_message(282, "Not existing class"))
        return [iuser, imagic, response]

    classid, skillname, trainerid, fullname, note, when, _max, status, attendeename = _class[:9]

    # check if user is trainer; only trainer can update attendees' state
    # have to be the trainer for THAT class
    if trainerid != userid:
        response.append(build_response_message(283, "You aren't the trainer of this class"))
        return [iuser, imagic, response]

    # check if state is correct input
    if state not in ["pass", "fail", "remove"]:
        response.append(build_response_message(284, "Invalid state input"))
        return [iuser, imagic, response]

    # check if attendee enrolled or not
    if status != 0: #return error msg -- cannot be updated # must be enrolled to get removed
        response.append(build_response_message(281, "You aren't the attendee of the class"))
        return [iuser, imagic, response]

    # check date/time
    now = int(datetime.datetime.now().timestamp())
    start = int(when)

    if state == "remove":
    # do remove ---
        if now > start: # still on-going class status
            response.append(build_response_message(285, "Too late to do this action"))
            return [iuser, imagic, response]

        do_database_execute(f"UPDATE attendee SET status = 4 WHERE attendeeid = {attendeeid};")
        enrolled_attendee = do_database_fetchone(f"""SELECT COUNT (*)
                                                FROM attendee
                                                WHERE classid = {classid} AND status NOT IN (3,4);
                                                """)
        # find size
        size = enrolled_attendee[0]

        response.append(build_response_attendee(attendeeid, attendeename, "cancelled"))
        response.append(build_response_message(0, "Status updated: Cancelled"))
        response.append(
            build_response_class(
                classid, skillname, fullname, when, note, size, _max, "cancel"
                )
        )
        return [iuser, imagic, response]

    if now < start: # class hasn't yet started
        response.append(build_response_message(286, "Too early to do this action"))
        return [iuser, imagic, response]

    # do pass/fail ---
    if state == "pass":
        do_database_execute(f"UPDATE attendee SET status = 1 WHERE attendeeid = {attendeeid};")
        response.append(build_response_attendee(attendeeid, attendeename, "passed"))
        response.append(build_response_message(0, "Status updated: Passed"))

    if state == "fail":
        do_database_execute(f"UPDATE attendee SET status = 2 WHERE attendeeid = {attendeeid};")
        response.append(build_response_attendee(attendeeid, attendeename, "failed"))
        response.append(build_response_message(0, "Status updated: Failed"))

    return [iuser, imagic, response]

def handle_create_class_request(iuser, imagic, content):
    """This code handles a request to create a class."""

    response = []
    ## Add code here
    # content = {"id":create.html,"day":10,"month":1,
    #            "year":2022,"hour":15,"minute":40,"note":"asdfasdf", "max":6}
    #check any injection via iuser(username) or imagic
    if "'" in iuser or not imagic.isdigit():
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]
    # login_session
    session = do_database_fetchone(f"""
                                   SELECT session.userid 
                                   FROM session 
                                   JOIN users ON session.userid = users.userid
                                   WHERE username = '{iuser}' AND magic = {imagic};""")
    # if user not logging in, redirect to login page
    if not session:
        iuser = "!"
        response.append(build_response_redirect("/login.html"))
        return [iuser, imagic, response]

    userid = session[0]

    keys = ["id", "note", "max", "day", "month", "year", "hour", "minute"]
    for key in keys:
        if content.get(key) is None:
            response.append(build_response_message(190, "Missing parameter: " + key))
            return [iuser, imagic, response]

    skillid, note, _max, day, month, year, hour, minute = (content.get(key) for key in keys)

    # check note
    note = str(note)
    # avoid injection from note; check single quote
    if "'" in note:
        response.append(build_response_message(290, "Bad note"))
        return [iuser, imagic, response]

    # check if skillid is int type
    try:
        skillid = int(skillid)
    except ValueError:
        response.append(build_response_message(291, "Bad skillid"))
        return [iuser, imagic, response]

    # check if max is in (1,10)range
    try:
        _max = int(_max)
        if _max < 1 or _max > 10:
            raise ValueError("Out of range")
    except ValueError as va_er:
        response.append(build_response_message(292, f"Bad max value: {va_er}"))
        return [iuser, imagic, response]

    # check if day month year is int
    # check if day/month/year is valid date
    # check if hour minute is int
    # check if hour:minute is valid time
    # check if day/month/year hour:minute is beyond the current time
    try:
        start = datetime.datetime(year, month, day, hour, minute)
        start = int(start.timestamp())
        if start < int(datetime.datetime.now().timestamp()):
            raise ValueError("Datetime is in the past")
    except ValueError as va_er:
        response.append(build_response_message(293, f"Bad datetime: {va_er}"))
        return [iuser, imagic, response]

    # check if iuser = trainerid and skillid = skillid on trainer table
    skill = do_database_fetchone(f"""
                                SELECT COUNT(*) 
                                FROM trainer 
                                WHERE skillid = {skillid} AND trainerid = {userid};""")
    # check if user is the trainer for given skill
    if skill[0] == 0:
        response.append(build_response_message(294, "Bad skillid"))
        return [iuser, imagic, response]

    # if valid: insert a row into class table and select last_insert_rowid()
    do_database_execute(f"""
                        INSERT INTO class (trainerid, skillid, start, max, note)
                        VALUES ({userid}, {skillid}, '{start}', {_max}, '{note}');""")
    # class data
    _class = do_database_fetchone(f"""SELECT classid
                                  FROM class 
                                  WHERE trainerid = {userid} AND skillid = {skillid}
                                  ORDER BY classid DESC
                                  LIMIT 1;""")

    # append the msg and redirect responses
    #response.append(build_response_message(0, "Successfully created class"))
    response.append(build_response_redirect(f'/class/{_class[0]}'))
    return [iuser, imagic, response]

# HTTPRequestHandler class
class myHTTPServer_RequestHandler(BaseHTTPRequestHandler):

    # POST This function responds to GET requests to the web server.
    def do_POST(self):

        # The set_cookies function adds/updates two cookies returned with a webpage.
        # These identify the user who is logged in. The first parameter identifies the user
        # and the second should be used to verify the login session.
        def set_cookies(x, user, magic):
            ucookie = Cookie.SimpleCookie()
            ucookie['u_cookie'] = user
            x.send_header("Set-Cookie", ucookie.output(header='', sep=''))
            mcookie = Cookie.SimpleCookie()
            mcookie['m_cookie'] = magic
            x.send_header("Set-Cookie", mcookie.output(header='', sep=''))

        # The get_cookies function returns the values of the user and magic cookies if they exist
        # it returns empty strings if they do not.
        def get_cookies(source):
            rcookies = Cookie.SimpleCookie(source.headers.get('Cookie'))
            user = ''
            magic = ''
            for keyc, valuec in rcookies.items():
                if keyc == 'u_cookie':
                    user = valuec.value
                if keyc == 'm_cookie':
                    magic = valuec.value
            return [user, magic]

        # Fetch the cookies that arrived with the GET request
        # The identify the user session.
        user_magic = get_cookies(self)

        print(user_magic)

        # Parse the GET request to identify the file requested and the parameters
        parsed_path = urllib.parse.urlparse(self.path)

        # Decided what to do based on the file requested.

        # The special file 'action' is not a real file, it indicates an action
        # we wish the server to execute.
        if parsed_path.path == '/action':
            self.send_response(200) #respond that this is a valid page request

            # extract the content from the POST request.
            # This are passed to the handlers.
            length = int(self.headers.get('Content-Length'))
            scontent = self.rfile.read(length).decode('ascii')
            print(scontent)
            if length > 0:
                content = json.loads(scontent)
            else:
                content = []

            # deal with get parameters
            parameters = urllib.parse.parse_qs(parsed_path.query)

            if 'command' in parameters:
                # check if one of the parameters was 'command'
                # If it is, identify which command and call the appropriate handler function.
                # You should not need to change this code.
                if parameters['command'][0] == 'login':
                    [user, magic, response] = handle_login_request(user_magic[0], user_magic[1], content)
                    #The result of a login attempt will be to set the cookies to identify the session.
                    set_cookies(self, user, magic)
                elif parameters['command'][0] == 'logout':
                    [user, magic, response] = handle_logout_request(user_magic[0], user_magic[1], parameters)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'get_my_skills':
                    [user, magic, response] = handle_get_my_skills_request(user_magic[0], user_magic[1])
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'get_upcoming':
                    [user, magic, response] = handle_get_upcoming_request(user_magic[0], user_magic[1])
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'join_class':
                    [user, magic, response] = handle_join_class_request(user_magic[0], user_magic[1], content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'leave_class':
                    [user, magic, response] = handle_leave_class_request(user_magic[0], user_magic[1], content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'get_class':
                    [user, magic, response] = handle_get_class_detail_request(user_magic[0], user_magic[1], content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'update_attendee':
                    [user, magic, response] = handle_update_attendee_request(user_magic[0], user_magic[1], content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'cancel_class':
                    [user, magic, response] = handle_cancel_class_request(user_magic[0], user_magic[1], content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'create_class':
                    [user, magic, response] = handle_create_class_request(user_magic[0], user_magic[1], content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                else:
                    # The command was not recognised, report that to the user.
                    # This uses a special error code that is not part of the codes you will use.
                    response = []
                    response.append(
                        build_response_message(901, 'Internal Error: Command not recognised.')
                    )

            else:
                # There was no command present, report that to the user.
                # This uses a special error code that is not part of the codes you will use.
                response = []
                response.append(build_response_message(902, 'Internal Error: Command not found.'))

            text = json.dumps(response)
            print(text)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(text, 'utf-8'))

        else:
            # A file that does n't fit one of the patterns above was requested.
            self.send_response(404) # a file not found html response
            self.end_headers()
        return

   # GET This function responds to GET requests to the web server.
   # You should not need to change this function.
    def do_GET(self):

        # Parse the GET request to identify the file requested and the parameters
        parsed_path = urllib.parse.urlparse(self.path)

        # Decided what to do based on the file requested.

        # Return a CSS (Cascading Style Sheet) file.
        # These tell the web client how the page should appear.
        if self.path.startswith('/css'):
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()
            with open('.'+self.path, 'rb') as file:
                self.wfile.write(file.read())

        # Return a Javascript file.
        # These contain code that the web client can execute.
        elif self.path.startswith('/js'):
            self.send_response(200)
            self.send_header('Content-type', 'text/js')
            self.end_headers()
            with open('.'+self.path, 'rb') as file:
                self.wfile.write(file.read())

        # A special case of '/' means return the index.html (homepage)
        # of a website
        elif parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages/index.html', 'rb') as file:
                self.wfile.write(file.read())

        # Pages of the form /create/... will return the file create.html as content
        # The ... will be a class id
        elif parsed_path.path.startswith('/class/'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages/class.html', 'rb') as file:
                self.wfile.write(file.read())

        # Pages of the form /create/... will return the file create.html as content
        # The ... will be a skill id
        elif parsed_path.path.startswith('/create/'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages/create.html', 'rb') as file:
                self.wfile.write(file.read())

        # Return html pages.
        elif parsed_path.path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages'+parsed_path.path, 'rb') as file:
                self.wfile.write(file.read())
        else:
            # A file that does n't fit one of the patterns above was requested.
            self.send_response(404)
            self.end_headers()

        return

def run():
    """This is the entry point function to this code."""
    print('starting server...')
    ## You can add any extra start up code here
    # Server settings
    # When testing you should supply a command line argument in the 8081+ range

    # Changing code below this line may break the test environment.
    # There is no good reason to do so.
    if len(sys.argv) < 2: # Check we were given both the script name and a port number
        print("Port argument not provided.")
        return
    server_address = ('127.0.0.1', int(sys.argv[1]))
    httpd = HTTPServer(server_address, myHTTPServer_RequestHandler)
    print('running server on port =', sys.argv[1], '...')
    httpd.serve_forever() # This function will not return till the server is aborted.

run()
