# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Entry', fields ['headword', 'creation_datetime']
        db.delete_unique('lexicography_entry', ['headword', 'creation_datetime'])

        # Adding model 'Chunk'
        db.create_table('lexicography_chunk', (
            ('c_hash', self.gf('django.db.models.fields.CharField')(max_length=40, primary_key=True)),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('lexicography', ['Chunk'])

        # Adding model 'ChangeRecord'
        db.create_table('lexicography_changerecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('entry', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lexicography.Entry'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('session', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('ctype', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('csubtype', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('c_hash', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lexicography.Chunk'])),
        ))
        db.send_create_signal('lexicography', ['ChangeRecord'])

        # Adding unique constraint on 'ChangeRecord', fields ['entry', 'datetime', 'ctype']
        db.create_unique('lexicography_changerecord', ['entry_id', 'datetime', 'ctype'])

        # Adding unique constraint on 'Entry', fields ['creation_datetime', 'data']
        db.create_unique('lexicography_entry', ['creation_datetime', 'data'])


    def backwards(self, orm):
        # Removing unique constraint on 'Entry', fields ['creation_datetime', 'data']
        db.delete_unique('lexicography_entry', ['creation_datetime', 'data'])

        # Removing unique constraint on 'ChangeRecord', fields ['entry', 'datetime', 'ctype']
        db.delete_unique('lexicography_changerecord', ['entry_id', 'datetime', 'ctype'])

        # Deleting model 'Chunk'
        db.delete_table('lexicography_chunk')

        # Deleting model 'ChangeRecord'
        db.delete_table('lexicography_changerecord')

        # Adding unique constraint on 'Entry', fields ['headword', 'creation_datetime']
        db.create_unique('lexicography_entry', ['headword', 'creation_datetime'])


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
            'Meta': {'unique_together': "(('data', 'creation_datetime'),)", 'object_name': 'Entry'},
            'creation_datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'headword': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['lexicography']