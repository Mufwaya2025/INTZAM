from django.contrib import admin

from .models import (
    WebsiteAudience,
    WebsiteFAQ,
    WebsiteLead,
    WebsitePage,
    WebsitePageBlock,
    WebsitePageSection,
    WebsiteSettings,
    WebsiteTestimonial,
)


class WebsitePageSectionInline(admin.StackedInline):
    model = WebsitePageSection
    extra = 0
    fields = (
        'title',
        'subtitle',
        'body',
        'layout',
        'style',
        'image',
        'image_alt',
        'cta_text',
        'cta_url',
        'order',
        'is_active',
    )
    ordering = ('order', 'id')


class WebsitePageBlockInline(admin.StackedInline):
    model = WebsitePageBlock
    extra = 0
    fields = (
        'title',
        'subtitle',
        'body',
        'badge',
        'value',
        'image',
        'image_alt',
        'cta_text',
        'cta_url',
        'order',
        'is_active',
    )
    ordering = ('order', 'id')


@admin.register(WebsiteSettings)
class WebsiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'country_name', 'contact_email', 'contact_phone', 'updated_at']
    fieldsets = (
        ('Brand', {'fields': ('site_name', 'site_tagline', 'country_name')}),
        ('Homepage Hero', {'fields': (
            'hero_eyebrow', 'hero_title', 'hero_description',
            'hero_primary_cta_text', 'hero_primary_cta_url',
            'hero_secondary_cta_text', 'hero_secondary_cta_url',
        )}),
        ('Audience Messaging', {'fields': ('zambia_focus_copy', 'audience_intro')}),
        ('Lead Form', {'fields': ('lead_form_title', 'lead_form_description')}),
        ('Portal Links & Contact', {'fields': ('client_portal_url', 'staff_portal_url', 'contact_email', 'contact_phone')}),
    )


@admin.register(WebsitePage)
class WebsitePageAdmin(admin.ModelAdmin):
    list_display = ['navigation_label', 'slug', 'template', 'show_in_nav', 'nav_order', 'is_active']
    list_editable = ['show_in_nav', 'nav_order', 'is_active']
    search_fields = ['navigation_label', 'slug', 'hero_title', 'hero_description']
    list_filter = ['template', 'show_in_nav', 'is_active']
    prepopulated_fields = {'slug': ('navigation_label',)}
    inlines = [WebsitePageSectionInline]
    fieldsets = (
        ('Page Identity', {'fields': ('navigation_label', 'slug', 'template', 'show_in_nav', 'nav_order', 'is_active')}),
        ('Hero Copy', {'fields': ('eyebrow', 'hero_title', 'hero_description')}),
        ('Hero Actions', {'fields': ('hero_primary_cta_text', 'hero_primary_cta_url', 'hero_secondary_cta_text', 'hero_secondary_cta_url')}),
        ('Hero Media', {'fields': ('hero_image', 'hero_image_alt')}),
        ('SEO', {'fields': ('seo_title', 'seo_description')}),
    )


@admin.register(WebsitePageSection)
class WebsitePageSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'page', 'layout', 'style', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['layout', 'style', 'is_active', 'page']
    search_fields = ['title', 'subtitle', 'body', 'page__navigation_label']
    inlines = [WebsitePageBlockInline]


@admin.register(WebsitePageBlock)
class WebsitePageBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'badge', 'value', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'section__page']
    search_fields = ['title', 'subtitle', 'body', 'badge', 'section__title']


@admin.register(WebsiteAudience)
class WebsiteAudienceAdmin(admin.ModelAdmin):
    list_display = ['name', 'badge', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'description']


@admin.register(WebsiteFAQ)
class WebsiteFAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['question', 'answer']


@admin.register(WebsiteTestimonial)
class WebsiteTestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'role', 'quote']


@admin.register(WebsiteLead)
class WebsiteLeadAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'segment', 'status', 'created_at']
    list_filter = ['segment', 'status', 'created_at']
    search_fields = ['full_name', 'phone', 'email', 'employer_name']
