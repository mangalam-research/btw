# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Entry'
        db.create_table('lexicography_entry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('headword', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('creation_datetime', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('lexicography', ['Entry'])

        # Adding unique constraint on 'Entry', fields ['headword', 'creation_datetime']
        db.create_unique('lexicography_entry', ['headword', 'creation_datetime'])


    def backwards(self, orm):
        # Removing unique constraint on 'Entry', fields ['headword', 'creation_datetime']
        db.delete_unique('lexicography_entry', ['headword', 'creation_datetime'])

        # Deleting model 'Entry'
        db.delete_table('lexicography_entry')


    models = {
        'lexicography.entry': {
            'Meta': {'unique_together': "(('headword', 'creation_datetime'),)", 'object_name': 'Entry'},
            'creation_datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'headword': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['lexicography']