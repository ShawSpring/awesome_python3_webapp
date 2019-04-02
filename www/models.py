'''
models for user,blog,comment
'''
__author__ = 'xcl'

import time, uuid
from orm import Model, StringField, IntegerField, BooleanField, TextField, FloatField,create_pool


def next_id():
    return "%015d%s000" % (int(time.time()) * 1000, uuid.uuid4().hex)


class User(Model):
    __tablename__ = 'users'
    id = StringField(primarykey=True,default=next_id,ddl='varchar(50)')
    name = StringField(ddl="varchar(50)")
    admin=BooleanField()
    email = StringField(ddl="varchar(50)")
    passwd = StringField(ddl="varchar(50)")
    image=StringField(ddl="varchar(500)")
    created_at =  StringField(default = time.time)


class Blog(Model):
    __tablename__ = 'blogs'
    id = StringField(primarykey=True,default=next_id,ddl='varchar(50)')
    user_id = StringField(ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50")
    user_image=StringField(ddl="varchar(500)")
    name = StringField(ddl="varchar(50)")
    summary = StringField(ddl="varchar(200)")
    content = TextField()
    created_at =  StringField(default = time.time)

class comment(Model):
    __tablename__ = 'comments'
    id = StringField(primarykey=True,default=next_id,ddl='varchar(50)')
    blog_id = StringField(ddl="varchar(50)")
    user_id = StringField(ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50")
    user_image=StringField(ddl="varchar(500)")
    content = TextField()
    created_at =  StringField(default = time.time)

