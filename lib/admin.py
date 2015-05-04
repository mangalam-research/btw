from django.contrib import admin

class LimitedAdminSite(admin.AdminSite):
    site_header = "CMS Administration"
    site_title = "CMS Administration"

limited_admin_site = LimitedAdminSite()
