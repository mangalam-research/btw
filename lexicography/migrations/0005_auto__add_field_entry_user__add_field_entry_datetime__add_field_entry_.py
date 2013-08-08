# -*- coding: utf-8 -*-
import datetime
from django.utils.timezone import utc
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Entry.user'
        db.add_column('lexicography_entry', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True),
                      keep_default=False)

        # Adding field 'Entry.datetime'
        db.add_column('lexicography_entry', 'datetime',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, default=datetime.datetime.utcnow().replace(tzinfo=utc), blank=True),
                      keep_default=False)

        # Adding field 'Entry.session'
        db.add_column('lexicography_entry', 'session',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True),
                      keep_default=False)

        # Adding field 'Entry.ctype'
        db.add_column('lexicography_entry', 'ctype',
                      self.gf('django.db.models.fields.CharField')(default='C', max_length=1),
                      keep_default=False)

        # Adding field 'Entry.csubtype'
        db.add_column('lexicography_entry', 'csubtype',
                      self.gf('django.db.models.fields.CharField')(default='M', max_length=1),
                      keep_default=False)

        # Adding field 'Entry.c_hash'
        db.add_column('lexicography_entry', 'c_hash',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lexicography.Chunk'], null=True),
                      keep_default=False)

        # Adding unique constraint on 'Entry', fields ['headword']
        db.create_unique('lexicography_entry', ['headword'])

        # Adding field 'ChangeRecord.headword'
        db.add_column('lexicography_changerecord', 'headword',
                      self.gf('django.db.models.fields.CharField')(default='q', max_length=1024),
                      keep_default=False)


    def backwards(self, orm):
        # Removing unique constraint on 'Entry', fields ['headword']
        db.delete_unique('lexicography_entry', ['headword'])

        # Deleting field 'Entry.user'
        db.delete_column('lexicography_entry', 'user_id')

        # Deleting field 'Entry.datetime'
        db.delete_column('lexicography_entry', 'datetime')

        # Deleting field 'Entry.session'
        db.delete_column('lexicography_entry', 'session')

        # Deleting field 'Entry.ctype'
        db.delete_column('lexicography_entry', 'ctype')

        # Deleting field 'Entry.csubtype'
        db.delete_column('lexicography_entry', 'csubtype')

        # Deleting field 'Entry.c_hash'
        db.delete_column('lexicography_entry', 'c_hash_id')

        # Deleting field 'ChangeRecord.headword'
        db.delete_column('lexicography_changerecord', 'headword')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lexicography.changerecord': {
            'Meta': {'unique_together': "(('entry', 'datetime', 'ctype'),)", 'object_name': 'ChangeRecord'},
            'c_hash': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lexicography.Chunk']"}),
            'csubtype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lexicography.Entry']"}),
            'headword': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'lexicography.chunk': {
            'Meta': {'object_name': 'Chunk'},
            'c_hash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {})
        },
        'lexicography.entry': {
            'Meta': {'object_name': 'Entry'},
            'c_hash': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lexicography.Chunk']", 'null': 'True'}),
            'csubtype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'headword': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        }
    }

    complete_apps = ['lexicography']
