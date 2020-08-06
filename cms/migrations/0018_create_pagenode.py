# -*- coding: utf-8 -*-
import django
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion

from . import IrreversibleMigration


def get_descendants(root):
    """
    Returns the a generator of primary keys which represent
    descendants of the given page ID (root_id)
    """
    # Note this is done because get_descendants() can't be trusted
    # as the tree can be corrupt.

    for child in root.children.order_by('path').iterator():
        yield child

        for child in get_descendants(child):
            yield child


def create_page_nodes(apps, schema_editor):
    Page = apps.get_model('cms', 'Page')
    TreeNode = apps.get_model('cms', 'TreeNode')
    db_alias = schema_editor.connection.alias
    root_draft_pages = Page.objects.using(db_alias).filter(
        publisher_is_draft=True,
        parent__isnull=True,
    )

    create_node = TreeNode.objects.using(db_alias).create

    nodes_by_page = {}

    for root in root_draft_pages:
        node = create_node(
            site_id=root.site_id,
            path=root.path,
            depth=root.depth,
            numchild=root.numchild,
            parent=None,
        )

        nodes_by_page[root.pk] = node

        for descendant in get_descendants(root):
            node = create_node(
                site_id=descendant.site_id,
                path=descendant.path,
                depth=descendant.depth,
                numchild=descendant.numchild,
                parent=nodes_by_page[descendant.parent_id],
            )
            nodes_by_page[descendant.pk] = node


class Migration(IrreversibleMigration):

    dependencies = [
        ('sites', '0001_initial'),
        ('cms', '0017_pagetype'),
    ]
    replaces = [('cms', '0018_pagenode')]

    operations = [
        migrations.CreateModel(
            name='TreeNode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(max_length=255, unique=True)),
                ('depth', models.PositiveIntegerField()),
                ('numchild', models.PositiveIntegerField(default=0)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='cms.TreeNode')),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='djangocms_nodes', to='sites.Site', verbose_name='site')),
            ],
            options={
                'ordering': ('path',),
                'default_permissions': [],
            },
        ),
        migrations.RunPython(create_page_nodes),
        migrations.AddField(
            model_name='page',
            name='node',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cms_pages',
                                    to='cms.TreeNode'),
        ),
        migrations.AddField(
            model_name='page',
            name='migration_0018_control',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterUniqueTogether(
            name='page',
            unique_together=set([('node', 'publisher_is_draft')]),
        ),
        migrations.AlterModelManagers(
            name='pageusergroup',
            managers=[
                ('objects', django.contrib.auth.models.GroupManager()),
            ],
        ),
    ]
