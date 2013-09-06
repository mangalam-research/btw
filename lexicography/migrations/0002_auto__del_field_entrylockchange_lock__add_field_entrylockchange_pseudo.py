# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'EntryLockChange.lock'
        db.delete_column(u'lexicography_entrylockchange', 'lock_id')

        # Adding field 'EntryLockChange.pseudo_id'
        db.add_column(u'lexicography_entrylockchange', 'pseudo_id',
                      self.gf('django.db.models.fields.DateTimeField')(default='1900-1-1'),
                      keep_default=False)

        # Adding field 'EntryLockChange.csubtype'
        db.add_column(u'lexicography_entrylockchange', 'csubtype',
                      self.gf('django.db.models.fields.CharField')(default='O', max_length=1),
                      keep_default=False)

        # Adding field 'EntryLock.pseudo_id'
        db.add_column(u'lexicography_entrylock', 'pseudo_id',
                      self.gf('django.db.models.fields.DateTimeField')(default='1900-1-1'),
                      keep_default=False)

        # Adding field 'EntryLock.csubtype'
        db.add_column(u'lexicography_entrylock', 'csubtype',
                      self.gf('django.db.models.fields.CharField')(default='O', max_length=1),
                      keep_default=False)


    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'EntryLockChange.lock'
        raise RuntimeError("Cannot reverse this migration. 'EntryLockChange.lock' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'EntryLockChange.lock'
        db.add_column(u'lexicography_entrylockchange', 'lock',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lexicography.EntryLock']),
                      keep_default=False)

        # Deleting field 'EntryLockChange.pseudo_id'
        db.delete_column(u'lexicography_entrylockchange', 'pseudo_id')

        # Deleting field 'EntryLockChange.csubtype'
        db.delete_column(u'lexicography_entrylockchange', 'csubtype')

        # Deleting field 'EntryLock.pseudo_id'
        db.delete_column(u'lexicography_entrylock', 'pseudo_id')

        # Deleting field 'EntryLock.csubtype'
        db.delete_column(u'lexicography_entrylock', 'csubtype')


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
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
            'c_hash': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lexicography.Chunk']"}),
            'csubtype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lexicography.Entry']"}),
            'headword': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'lexicography.chunk': {
            'Meta': {'object_name': 'Chunk'},
            'c_hash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'is_normal': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'lexicography.entry': {
            'Meta': {'unique_together': "(('headword',),)", 'object_name': 'Entry'},
            'c_hash': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lexicography.Chunk']"}),
            'csubtype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'headword': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'lexicography.entrylock': {
            'Meta': {'unique_together': "(('entry',),)", 'object_name': 'EntryLock'},
            'csubtype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lexicography.Entry']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'lexicography_entrylock_entrylocks_initiated'", 'to': u"orm['auth.User']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'lexicography_entrylock_entrylocks_owned'", 'to': u"orm['auth.User']"}),
            'pseudo_id': ('django.db.models.fields.DateTimeField', [], {}),
            'session': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        u'lexicography.entrylockchange': {
            'Meta': {'object_name': 'EntryLockChange'},
            'csubtype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lexicography.Entry']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'lexicography_entrylockchange_entrylocks_initiated'", 'to': u"orm['auth.User']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'lexicography_entrylockchange_entrylocks_owned'", 'to': u"orm['auth.User']"}),
            'pseudo_id': ('django.db.models.fields.DateTimeField', [], {}),
            'session': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
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
