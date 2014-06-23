# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Entry'
        db.create_table(u'lexicography_entry', (
            (u'id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('headword', self.gf('django.db.models.fields.CharField')
             (max_length=1024)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['auth.User'])),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')()),
            ('session', self.gf('django.db.models.fields.CharField')
             (max_length=100, null=True)),
            ('ctype', self.gf('django.db.models.fields.CharField')
             (max_length=1)),
            ('csubtype', self.gf('django.db.models.fields.CharField')
             (max_length=1)),
            ('c_hash', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['lexicography.Chunk'])),
        ))
        db.send_create_signal(u'lexicography', ['Entry'])

        # Adding unique constraint on 'Entry', fields ['headword']
        db.create_unique(u'lexicography_entry', ['headword'])

        # Adding model 'ChangeRecord'
        db.create_table(u'lexicography_changerecord', (
            (u'id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('headword', self.gf('django.db.models.fields.CharField')
             (max_length=1024)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['auth.User'])),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')()),
            ('session', self.gf('django.db.models.fields.CharField')
             (max_length=100, null=True)),
            ('ctype', self.gf('django.db.models.fields.CharField')
             (max_length=1)),
            ('csubtype', self.gf('django.db.models.fields.CharField')
             (max_length=1)),
            ('c_hash', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['lexicography.Chunk'])),
            ('entry', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['lexicography.Entry'])),
        ))
        db.send_create_signal(u'lexicography', ['ChangeRecord'])

        # Adding unique constraint on 'ChangeRecord', fields ['entry',
        # 'datetime', 'ctype']
        db.create_unique(u'lexicography_changerecord',
                         ['entry_id', 'datetime', 'ctype'])

        # Adding model 'Chunk'
        db.create_table(u'lexicography_chunk', (
            ('c_hash', self.gf('django.db.models.fields.CharField')
             (max_length=40, primary_key=True)),
            ('is_normal', self.gf('django.db.models.fields.BooleanField')
             (default=True)),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'lexicography', ['Chunk'])

        # Adding model 'EntryLock'
        db.create_table(u'lexicography_entrylock', (
            (u'id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('entry', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['lexicography.Entry'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['auth.User'])),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal(u'lexicography', ['EntryLock'])

        # Adding unique constraint on 'EntryLock', fields ['entry']
        db.create_unique(u'lexicography_entrylock', ['entry_id'])

        # Adding model 'Authority'
        db.create_table(u'lexicography_authority', (
            (u'id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
        ))
        db.send_create_signal(u'lexicography', ['Authority'])

        # Adding model 'UserAuthority'
        db.create_table(u'lexicography_userauthority', (
            (u'authority_ptr', self.gf('django.db.models.fields.related.OneToOneField')
             (to=orm[
                 'lexicography.Authority'], unique=True, primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['auth.User'])),
        ))
        db.send_create_signal(u'lexicography', ['UserAuthority'])

        # Adding model 'OtherAuthority'
        db.create_table(u'lexicography_otherauthority', (
            (u'authority_ptr', self.gf('django.db.models.fields.related.OneToOneField')
             (to=orm[
                 'lexicography.Authority'], unique=True, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')
             (max_length=1024)),
        ))
        db.send_create_signal(u'lexicography', ['OtherAuthority'])

        # Adding model 'Handle'
        db.create_table(u'lexicography_handle', (
            (u'id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('session', self.gf('django.db.models.fields.CharField')
             (max_length=100)),
            ('handle', self.gf('django.db.models.fields.IntegerField')()),
            ('entry', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['lexicography.Entry'], null=True)),
        ))
        db.send_create_signal(u'lexicography', ['Handle'])

        # Adding unique constraint on 'Handle', fields ['session', 'handle']
        db.create_unique(u'lexicography_handle', ['session', 'handle'])

        # Adding unique constraint on 'Handle', fields ['session', 'entry']
        db.create_unique(u'lexicography_handle', ['session', 'entry_id'])

    def backwards(self, orm):
        # Removing unique constraint on 'Handle', fields ['session', 'entry']
        db.delete_unique(u'lexicography_handle', ['session', 'entry_id'])

        # Removing unique constraint on 'Handle', fields ['session', 'handle']
        db.delete_unique(u'lexicography_handle', ['session', 'handle'])

        # Removing unique constraint on 'EntryLock', fields ['entry']
        db.delete_unique(u'lexicography_entrylock', ['entry_id'])

        # Removing unique constraint on 'ChangeRecord', fields ['entry',
        # 'datetime', 'ctype']
        db.delete_unique(u'lexicography_changerecord',
                         ['entry_id', 'datetime', 'ctype'])

        # Removing unique constraint on 'Entry', fields ['headword']
        db.delete_unique(u'lexicography_entry', ['headword'])

        # Deleting model 'Entry'
        db.delete_table(u'lexicography_entry')

        # Deleting model 'ChangeRecord'
        db.delete_table(u'lexicography_changerecord')

        # Deleting model 'Chunk'
        db.delete_table(u'lexicography_chunk')

        # Deleting model 'EntryLock'
        db.delete_table(u'lexicography_entrylock')

        # Deleting model 'Authority'
        db.delete_table(u'lexicography_authority')

        # Deleting model 'UserAuthority'
        db.delete_table(u'lexicography_userauthority')

        # Deleting model 'OtherAuthority'
        db.delete_table(u'lexicography_otherauthority')

        # Deleting model 'Handle'
        db.delete_table(u'lexicography_handle')

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
