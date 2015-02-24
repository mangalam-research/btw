# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ZoteroUser'
        db.create_table(u'bibliography_zoterouser', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('btw_user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('uid', self.gf('bibliography.models.ZoteroUIDField')(max_length=22)),
            ('api_key', self.gf('bibliography.models.ZoteroAPIKeyField')(max_length=48)),
        ))
        db.send_create_signal(u'bibliography', ['ZoteroUser'])

        # Adding model 'Item'
        db.create_table(u'bibliography_item', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uid', self.gf('bibliography.models.ZoteroUIDField')(max_length=22)),
            ('item_key', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('date', self.gf('django.db.models.fields.TextField')(null=True)),
            ('title', self.gf('django.db.models.fields.TextField')(null=True)),
            ('creators', self.gf('django.db.models.fields.TextField')(null=True)),
            ('freshness', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('item', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal(u'bibliography', ['Item'])

        # Adding model 'PrimarySource'
        db.create_table(u'bibliography_primarysource', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('reference_title', self.gf('django.db.models.fields.TextField')(default=None, unique=True)),
            ('genre', self.gf('django.db.models.fields.CharField')(default=None, max_length=2)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='primary_sources', to=orm['bibliography.Item'])),
        ))
        db.send_create_signal(u'bibliography', ['PrimarySource'])


    def backwards(self, orm):
        # Deleting model 'ZoteroUser'
        db.delete_table(u'bibliography_zoterouser')

        # Deleting model 'Item'
        db.delete_table(u'bibliography_item')

        # Deleting model 'PrimarySource'
        db.delete_table(u'bibliography_primarysource')


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
        u'bibliography.item': {
            'Meta': {'object_name': 'Item'},
            'creators': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'date': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'freshness': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'item_key': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'title': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'uid': ('bibliography.models.ZoteroUIDField', [], {'max_length': '22'})
        },
        u'bibliography.primarysource': {
            'Meta': {'object_name': 'PrimarySource'},
            'genre': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'primary_sources'", 'to': u"orm['bibliography.Item']"}),
            'reference_title': ('django.db.models.fields.TextField', [], {'default': 'None', 'unique': 'True'})
        },
        u'bibliography.zoterouser': {
            'Meta': {'object_name': 'ZoteroUser'},
            'api_key': ('bibliography.models.ZoteroAPIKeyField', [], {'max_length': '48'}),
            'btw_user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'uid': ('bibliography.models.ZoteroUIDField', [], {'max_length': '22'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['bibliography']