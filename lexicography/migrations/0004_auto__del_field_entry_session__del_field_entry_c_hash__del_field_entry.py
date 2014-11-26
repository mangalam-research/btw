# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Entry.session'
        db.delete_column(u'lexicography_entry', 'session')

        # Deleting field 'Entry.c_hash'
        db.delete_column(u'lexicography_entry', 'c_hash_id')

        # Deleting field 'Entry.user'
        db.delete_column(u'lexicography_entry', 'user_id')

        # Deleting field 'Entry.csubtype'
        db.delete_column(u'lexicography_entry', 'csubtype')

        # Deleting field 'Entry.ctype'
        db.delete_column(u'lexicography_entry', 'ctype')

        # Deleting field 'Entry.datetime'
        db.delete_column(u'lexicography_entry', 'datetime')


    def backwards(self, orm):
        # Adding field 'Entry.session'
        db.add_column(u'lexicography_entry', 'session',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Entry.c_hash'
        raise RuntimeError("Cannot reverse this migration. 'Entry.c_hash' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'Entry.c_hash'
        db.add_column(u'lexicography_entry', 'c_hash',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lexicography.Chunk'], on_delete=models.PROTECT),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Entry.user'
        raise RuntimeError("Cannot reverse this migration. 'Entry.user' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'Entry.user'
        db.add_column(u'lexicography_entry', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], on_delete=models.PROTECT),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Entry.csubtype'
        raise RuntimeError("Cannot reverse this migration. 'Entry.csubtype' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'Entry.csubtype'
        db.add_column(u'lexicography_entry', 'csubtype',
                      self.gf('django.db.models.fields.CharField')(max_length=1),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Entry.ctype'
        raise RuntimeError("Cannot reverse this migration. 'Entry.ctype' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'Entry.ctype'
        db.add_column(u'lexicography_entry', 'ctype',
                      self.gf('django.db.models.fields.CharField')(max_length=1),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Entry.datetime'
        raise RuntimeError("Cannot reverse this migration. 'Entry.datetime' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'Entry.datetime'
        db.add_column(u'lexicography_entry', 'datetime',
                      self.gf('django.db.models.fields.DateTimeField')(),
                      keep_default=False)


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'lexicography.authority': {
            'Meta': {'object_name': 'Authority'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'lexicography.changerecord': {
            'Meta': {'unique_together': "(('entry', 'datetime', 'ctype'),)", 'object_name': 'ChangeRecord'},
            'c_hash': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lexicography.Chunk']", 'on_delete': 'models.PROTECT'}),
            'csubtype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lexicography.Entry']"}),
            'headword': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'on_delete': 'models.PROTECT'})
        },
        u'lexicography.chunk': {
            'Meta': {'object_name': 'Chunk'},
            'c_hash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'is_normal': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'lexicography.entry': {
            'Meta': {'unique_together': "(('headword',),)", 'object_name': 'Entry'},
            'headword': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'lexicography.entrylock': {
            'Meta': {'unique_together': "(('entry',),)", 'object_name': 'EntryLock'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lexicography.Entry']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'lexicography.handle': {
            'Meta': {'unique_together': "(('session', 'handle'), ('session', 'entry'))", 'object_name': 'Handle'},
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lexicography.Entry']", 'null': 'True'}),
            'handle': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'lexicography.otherauthority': {
            'Meta': {'object_name': 'OtherAuthority', '_ormbases': [u'lexicography.Authority']},
            u'authority_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['lexicography.Authority']", 'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
        },
        u'lexicography.userauthority': {
            'Meta': {'object_name': 'UserAuthority', '_ormbases': [u'lexicography.Authority']},
            u'authority_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['lexicography.Authority']", 'unique': 'True', 'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['lexicography']