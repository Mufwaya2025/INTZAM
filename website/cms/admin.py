from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    PublicLoanProduct,
    WebsiteAudience,
    WebsiteFAQ,
    WebsiteLead,
    WebsitePage,
    WebsitePageBlock,
    WebsitePageSection,
    WebsiteSettings,
    WebsiteTestimonial,
)


admin.site.site_header = 'IntZam Website Editor'
admin.site.site_title = 'IntZam Website Admin'
admin.site.index_title = 'Content Dashboard'


def build_live_page_url(slug):
    return '/' if slug == 'home' else f'/{slug}/'


def render_admin_image_preview(file_field, empty_message, max_width=320):
    if not file_field:
        return empty_message
    return format_html(
        '<img src="{}" alt="Preview" style="max-width: {}px; width: 100%; border-radius: 16px; border: 1px solid #e5e7eb; box-shadow: 0 8px 24px rgba(15,23,42,0.08);" />',
        file_field.url,
        max_width,
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
        'image_preview',
        'ordering_guidance',
        'cta_text',
        'cta_url',
        'order',
        'is_active',
    )
    ordering = ('order', 'id')
    readonly_fields = ('image_preview', 'ordering_guidance')

    @admin.display(description='Section image preview')
    def image_preview(self, obj):
        return render_admin_image_preview(getattr(obj, 'image', None), 'No section image uploaded yet')

    @admin.display(description='Ordering guidance')
    def ordering_guidance(self, obj):
        return mark_safe(
            '<div style="max-width:700px; line-height:1.6; color:#475467;">'
            'Use the <strong>order</strong> field to control section sequence. '
            'Smaller numbers appear first. For easier future inserts, use gaps like '
            '<strong>10, 20, 30</strong> instead of 1, 2, 3.'
            '</div>'
        )


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
        'image_preview',
        'ordering_guidance',
        'cta_text',
        'cta_url',
        'order',
        'is_active',
    )
    ordering = ('order', 'id')
    readonly_fields = ('image_preview', 'ordering_guidance')

    @admin.display(description='Block image preview')
    def image_preview(self, obj):
        return render_admin_image_preview(getattr(obj, 'image', None), 'No block image uploaded yet', max_width=260)

    @admin.display(description='Ordering guidance')
    def ordering_guidance(self, obj):
        return mark_safe(
            '<div style="max-width:700px; line-height:1.6; color:#475467;">'
            'Use the <strong>order</strong> field to control block sequence within this section. '
            'Smaller numbers appear first; spacing values like <strong>10, 20, 30</strong> makes reordering easier.'
            '</div>'
        )


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
        ('Client Portal & Contact', {'fields': ('client_portal_url', 'contact_email', 'contact_phone')}),
    )


@admin.register(PublicLoanProduct)
class PublicLoanProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'interest_type', 'calculated_interest_rate', 'min_amount', 'max_amount', 'min_term', 'max_term', 'is_active']
    list_filter = ['interest_type', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name', 'description']
    fieldsets = (
        ('Product Details', {
            'fields': ('name', 'description', 'interest_type'),
        }),
        ('Pricing', {
            'fields': (
                'nominal_interest_rate',
                'credit_facilitation_fee',
                'processing_fee',
                'pricing_formula_note',
                'calculated_interest_rate',
            ),
        }),
        ('Eligibility & Display', {
            'fields': (
                'min_amount',
                'max_amount',
                'min_term',
                'max_term',
                'required_documents',
                'order',
                'is_active',
            ),
        }),
    )
    readonly_fields = ['pricing_formula_note', 'calculated_interest_rate']

    @admin.display(description='Pricing formula')
    def pricing_formula_note(self, obj):
        return mark_safe(
            '<div style="max-width:700px; line-height:1.6; color:#475467;">'
            'Total <strong>Interest rate</strong> is calculated automatically as:<br>'
            '<strong>Nominal interest rate + Credit facilitation fee + Processing fee</strong>.'
            '</div>'
        )

    @admin.display(description='Interest rate')
    def calculated_interest_rate(self, obj):
        if not obj.pk:
            return 'Calculated on save'
        return f'{obj.interest_rate}%'


@admin.register(WebsitePage)
class WebsitePageAdmin(admin.ModelAdmin):
    list_display = ['navigation_label', 'slug', 'template', 'show_in_nav', 'nav_order', 'is_active', 'live_page_link']
    list_editable = ['show_in_nav', 'nav_order', 'is_active']
    list_filter = ['template', 'show_in_nav', 'is_active']
    search_fields = ['navigation_label', 'slug', 'hero_title', 'hero_description']
    inlines = [WebsitePageSectionInline]
    fieldsets = (
        ('Page Identity', {'fields': ('navigation_label', 'slug', 'template', 'show_in_nav', 'nav_order', 'is_active', 'live_page_link')}),
        ('Hero Copy', {'fields': ('eyebrow', 'hero_title', 'hero_description')}),
        ('Hero Actions', {'fields': ('hero_primary_cta_text', 'hero_primary_cta_url', 'hero_secondary_cta_text', 'hero_secondary_cta_url')}),
        ('Page Media', {'fields': (
            'hero_image',
            'hero_image_alt',
            'hero_image_preview',
            'illustration_image',
            'illustration_image_alt',
            'illustration_image_preview',
        )}),
        ('SEO', {'fields': ('seo_title', 'seo_description')}),
    )
    readonly_fields = ['live_page_link', 'hero_image_preview', 'illustration_image_preview']

    @admin.display(description='Live page')
    def live_page_link(self, obj):
        if not getattr(obj, 'slug', None):
            return 'Save page first to enable preview'
        return format_html(
            '<a href="{}" target="_blank" rel="noreferrer" style="font-weight:600;">Open live page</a>',
            build_live_page_url(obj.slug),
        )

    @admin.display(description='Hero image preview')
    def hero_image_preview(self, obj):
        return render_admin_image_preview(getattr(obj, 'hero_image', None), 'No hero image uploaded yet', max_width=420)

    @admin.display(description='Illustration preview')
    def illustration_image_preview(self, obj):
        return render_admin_image_preview(getattr(obj, 'illustration_image', None), 'No illustration image uploaded yet')


@admin.register(WebsitePageSection)
class WebsitePageSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'page', 'layout', 'style', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['layout', 'style', 'is_active', 'page']
    search_fields = ['title', 'subtitle', 'body', 'page__navigation_label']
    inlines = [WebsitePageBlockInline]
    fieldsets = (
        ('Section Content', {
            'fields': ('page', 'page_preview_link', 'title', 'subtitle', 'body', 'layout', 'style', 'image', 'image_alt', 'image_preview')
        }),
        ('Calls To Action', {
            'fields': ('cta_text', 'cta_url')
        }),
        ('Ordering', {
            'fields': ('ordering_guidance', 'order', 'is_active')
        }),
    )
    readonly_fields = ('page_preview_link', 'image_preview', 'ordering_guidance')

    @admin.display(description='Live page')
    def page_preview_link(self, obj):
        if not getattr(obj, 'page', None):
            return 'Assign page to enable preview'
        return format_html(
            '<a href="{}" target="_blank" rel="noreferrer" style="font-weight:600;">Open parent page</a>',
            build_live_page_url(obj.page.slug),
        )

    @admin.display(description='Section image preview')
    def image_preview(self, obj):
        return render_admin_image_preview(getattr(obj, 'image', None), 'No section image uploaded yet')

    @admin.display(description='Ordering guidance')
    def ordering_guidance(self, obj):
        return mark_safe(
            '<div style="max-width:700px; line-height:1.6; color:#475467;">'
            'Sections render from lowest <strong>order</strong> to highest. '
            'Use spaced values like <strong>10, 20, 30</strong> so you can insert new sections later without renumbering everything.'
            '</div>'
        )


@admin.register(WebsitePageBlock)
class WebsitePageBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'badge', 'value', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'section__page']
    search_fields = ['title', 'subtitle', 'body', 'badge', 'section__title']
    fieldsets = (
        ('Block Content', {
            'fields': ('section', 'page_preview_link', 'title', 'subtitle', 'body', 'badge', 'value', 'image', 'image_alt', 'image_preview')
        }),
        ('Calls To Action', {
            'fields': ('cta_text', 'cta_url')
        }),
        ('Ordering', {
            'fields': ('ordering_guidance', 'order', 'is_active')
        }),
    )
    readonly_fields = ('page_preview_link', 'image_preview', 'ordering_guidance')

    @admin.display(description='Live page')
    def page_preview_link(self, obj):
        if not getattr(obj, 'section', None) or not getattr(obj.section, 'page', None):
            return 'Assign section to enable preview'
        return format_html(
            '<a href="{}" target="_blank" rel="noreferrer" style="font-weight:600;">Open parent page</a>',
            build_live_page_url(obj.section.page.slug),
        )

    @admin.display(description='Block image preview')
    def image_preview(self, obj):
        return render_admin_image_preview(getattr(obj, 'image', None), 'No block image uploaded yet', max_width=260)

    @admin.display(description='Ordering guidance')
    def ordering_guidance(self, obj):
        return mark_safe(
            '<div style="max-width:700px; line-height:1.6; color:#475467;">'
            'Blocks render within a section from lowest <strong>order</strong> to highest. '
            'Use spaced values like <strong>10, 20, 30</strong> to make future content changes easier.'
            '</div>'
        )


@admin.register(WebsiteAudience)
class WebsiteAudienceAdmin(admin.ModelAdmin):
    list_display = ['name', 'badge', 'order', 'is_active']
    list_editable = ['order', 'is_active']


@admin.register(WebsiteFAQ)
class WebsiteFAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'order', 'is_active']
    list_editable = ['order', 'is_active']


@admin.register(WebsiteTestimonial)
class WebsiteTestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'order', 'is_active']
    list_editable = ['order', 'is_active']


@admin.register(WebsiteLead)
class WebsiteLeadAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'segment', 'status', 'created_at']
    list_filter = ['segment', 'status', 'created_at']
    search_fields = ['full_name', 'phone', 'email', 'employer_name']
