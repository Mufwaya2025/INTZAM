from django.db import models
from django.utils.text import slugify


class WebsiteSettings(models.Model):
    site_name = models.CharField(max_length=100, default='IntZam')
    site_tagline = models.CharField(max_length=200, default='Smart Lending for Growing Communities')
    country_name = models.CharField(max_length=100, default='Zambia')
    hero_eyebrow = models.CharField(max_length=200, default='Fast. Clear. Human-centered lending.')
    hero_title = models.CharField(max_length=255, default='Beautiful digital lending for everyday ambition.')
    hero_description = models.TextField(default='IntZam helps individuals and growing businesses access flexible loans with transparent pricing, simple onboarding, and a modern mobile-first experience.')
    hero_primary_cta_text = models.CharField(max_length=100, default='Start an application')
    hero_primary_cta_url = models.CharField(max_length=255, default='/app/')
    hero_secondary_cta_text = models.CharField(max_length=100, default='Explore products')
    hero_secondary_cta_url = models.CharField(max_length=255, default='#products')
    client_portal_url = models.CharField(max_length=255, default='/app/')
    staff_portal_url = models.CharField(max_length=255, default='/admin-frontend/')
    zambia_focus_copy = models.CharField(max_length=255, default='Designed for Zambia\'s civil servants, salaried professionals, and growing households.')
    audience_intro = models.TextField(default='Especially relevant for civil servants, teachers, nurses, and other dependable earners who need a simpler, more respectful lending experience.')
    lead_form_title = models.CharField(max_length=255, default='Talk to IntZam about the right loan for you.')
    lead_form_description = models.TextField(default='Share a few details and our team can reach out, especially if you are a civil servant or salaried professional in Zambia.')
    contact_email = models.EmailField(default='hello@intzam.com')
    contact_phone = models.CharField(max_length=30, default='+260 000 000 000')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Website settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    def __str__(self):
        return f'{self.site_name} Website Settings'


class WebsiteAudience(models.Model):
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    name = models.CharField(max_length=120)
    badge = models.CharField(max_length=120, blank=True)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class WebsiteFAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.question


class WebsiteTestimonial(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    quote = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class WebsitePageTemplate(models.TextChoices):
    STANDARD = 'STANDARD', 'Standard'
    LANDING = 'LANDING', 'Landing'
    CALCULATOR = 'CALCULATOR', 'Calculator'
    CONTACT = 'CONTACT', 'Contact'


class WebsiteSectionLayout(models.TextChoices):
    TEXT = 'TEXT', 'Text'
    CARD_GRID = 'CARD_GRID', 'Card Grid'
    FEATURE_LIST = 'FEATURE_LIST', 'Feature List'
    STATS = 'STATS', 'Stats'
    CTA = 'CTA', 'Call To Action'


class WebsiteSectionStyle(models.TextChoices):
    DEFAULT = 'DEFAULT', 'Default'
    ALT = 'ALT', 'Alt Background'
    HIGHLIGHT = 'HIGHLIGHT', 'Highlight'


class WebsitePage(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    navigation_label = models.CharField(max_length=100)
    template = models.CharField(max_length=20, choices=WebsitePageTemplate.choices, default=WebsitePageTemplate.STANDARD)
    eyebrow = models.CharField(max_length=200, blank=True)
    hero_title = models.CharField(max_length=255)
    hero_description = models.TextField(blank=True)
    hero_primary_cta_text = models.CharField(max_length=100, blank=True)
    hero_primary_cta_url = models.CharField(max_length=255, blank=True)
    hero_secondary_cta_text = models.CharField(max_length=100, blank=True)
    hero_secondary_cta_url = models.CharField(max_length=255, blank=True)
    hero_image = models.ImageField(upload_to='website/hero/', null=True, blank=True)
    hero_image_alt = models.CharField(max_length=200, blank=True)
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.TextField(blank=True)
    show_in_nav = models.BooleanField(default=True)
    nav_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nav_order', 'navigation_label']

    def __str__(self):
        return self.navigation_label


class WebsitePageSection(models.Model):
    page = models.ForeignKey(WebsitePage, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    body = models.TextField(blank=True)
    layout = models.CharField(max_length=20, choices=WebsiteSectionLayout.choices, default=WebsiteSectionLayout.TEXT)
    style = models.CharField(max_length=20, choices=WebsiteSectionStyle.choices, default=WebsiteSectionStyle.DEFAULT)
    image = models.ImageField(upload_to='website/sections/', null=True, blank=True)
    image_alt = models.CharField(max_length=200, blank=True)
    cta_text = models.CharField(max_length=100, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.page.navigation_label} - {self.title}'


class WebsitePageBlock(models.Model):
    section = models.ForeignKey(WebsitePageSection, on_delete=models.CASCADE, related_name='blocks')
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    badge = models.CharField(max_length=120, blank=True)
    value = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to='website/blocks/', null=True, blank=True)
    image_alt = models.CharField(max_length=200, blank=True)
    cta_text = models.CharField(max_length=100, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class WebsiteLeadSegment(models.TextChoices):
    CIVIL_SERVANT = 'CIVIL_SERVANT', 'Civil Servant'
    TEACHER_OR_NURSE = 'TEACHER_OR_NURSE', 'Teacher or Nurse'
    SALARIED_EMPLOYEE = 'SALARIED_EMPLOYEE', 'Salaried Employee'
    BUSINESS_OWNER = 'BUSINESS_OWNER', 'Business Owner'
    OTHER = 'OTHER', 'Other'


class WebsiteLeadStatus(models.TextChoices):
    NEW = 'NEW', 'New'
    CONTACTED = 'CONTACTED', 'Contacted'
    QUALIFIED = 'QUALIFIED', 'Qualified'
    CONVERTED = 'CONVERTED', 'Converted'
    CLOSED = 'CLOSED', 'Closed'


class WebsiteLead(models.Model):
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    segment = models.CharField(max_length=30, choices=WebsiteLeadSegment.choices, default=WebsiteLeadSegment.CIVIL_SERVANT)
    employer_name = models.CharField(max_length=200, blank=True)
    desired_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    desired_term_months = models.PositiveIntegerField(null=True, blank=True)
    message = models.TextField(blank=True)
    consent = models.BooleanField(default=False)
    source_page = models.CharField(max_length=100, default='website')
    status = models.CharField(max_length=20, choices=WebsiteLeadStatus.choices, default=WebsiteLeadStatus.NEW)
    converted_client = models.ForeignKey('core.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='website_leads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} ({self.phone})'


def bootstrap_website_content():
    WebsiteSettings.get_solo()

    audiences = [
        {
            'slug': 'civil-servants',
            'name': 'Civil Servants',
            'badge': 'Priority audience',
            'description': 'Clear application flows and dependable support for public sector employees who value speed, trust, and predictable repayments.',
            'order': 1,
        },
        {
            'slug': 'teachers-and-nurses',
            'name': 'Teachers and Nurses',
            'badge': 'Everyday growth',
            'description': 'Flexible personal financing designed for professionals balancing family needs, school fees, transport, and household plans.',
            'order': 2,
        },
        {
            'slug': 'traders-and-small-businesses',
            'name': 'Traders and Small Businesses',
            'badge': 'Business momentum',
            'description': 'Working capital support for business owners who need fast access to structured, transparent financing.',
            'order': 3,
        },
    ]

    for audience in audiences:
        WebsiteAudience.objects.get_or_create(slug=audience['slug'], defaults=audience)

    faqs = [
        {
            'question': 'Who can apply for an IntZam loan?',
            'answer': 'Individuals and qualifying businesses can apply, subject to eligibility, KYC requirements, and internal review.',
            'order': 1,
        },
        {
            'question': 'Is IntZam suitable for civil servants in Zambia?',
            'answer': 'Yes. The public website and lead flow are now intentionally geared toward salaried professionals, especially civil servants and related public sector workers.',
            'order': 2,
        },
        {
            'question': 'Can I track my application status online?',
            'answer': 'Yes. The connected client portal is designed to help applicants view status updates, loan details, and repayment information.',
            'order': 3,
        },
        {
            'question': 'What information do I need to get started?',
            'answer': 'You typically need identity details, contact information, and any supporting financial or KYC documentation required for your product type.',
            'order': 4,
        },
    ]

    for faq in faqs:
        WebsiteFAQ.objects.get_or_create(question=faq['question'], defaults=faq)

    testimonials = [
        {
            'name': 'Grace M.',
            'role': 'Teacher in Lusaka',
            'quote': 'A modern lending website should feel clear, trustworthy, and respectful from the first step.',
            'order': 1,
        },
        {
            'name': 'Brian S.',
            'role': 'Public Service Officer',
            'quote': 'The best finance websites explain products simply and make it easy to ask for help.',
            'order': 2,
        },
        {
            'name': 'Chipo N.',
            'role': 'Small Business Owner',
            'quote': 'A strong digital front door makes the whole lending brand feel more professional and dependable.',
            'order': 3,
        },
    ]

    for testimonial in testimonials:
        WebsiteTestimonial.objects.get_or_create(
            name=testimonial['name'],
            role=testimonial['role'],
            defaults=testimonial,
        )

    page_defaults = [
        {
            'slug': 'home',
            'navigation_label': 'Home',
            'template': WebsitePageTemplate.LANDING,
            'eyebrow': 'Website editor',
            'hero_title': 'Launch richer public content around your lending platform.',
            'hero_description': 'Use admin-managed sections, blocks, and images to keep the public website fresh without changing code.',
            'hero_primary_cta_text': 'Apply Now',
            'hero_primary_cta_url': '/app/',
            'hero_secondary_cta_text': 'Open Calculator',
            'hero_secondary_cta_url': '/calculator/',
            'show_in_nav': False,
            'nav_order': 0,
        },
        {
            'slug': 'about',
            'navigation_label': 'About',
            'template': WebsitePageTemplate.STANDARD,
            'eyebrow': 'About IntZam',
            'hero_title': 'Built to make lending feel more human, clear, and dependable in Zambia.',
            'hero_description': 'Present your mission, values, and operating approach with a more polished and editable public experience.',
            'hero_primary_cta_text': 'Go to client portal',
            'hero_primary_cta_url': '/app/',
            'hero_secondary_cta_text': 'Try the calculator',
            'hero_secondary_cta_url': '/calculator/',
            'show_in_nav': True,
            'nav_order': 4,
        },
        {
            'slug': 'eligibility',
            'navigation_label': 'Eligibility',
            'template': WebsitePageTemplate.STANDARD,
            'eyebrow': 'Eligibility guide',
            'hero_title': 'Simple guidance before you begin your application.',
            'hero_description': 'Help visitors understand what is commonly needed before they apply, especially salaried borrowers and civil servants.',
            'hero_primary_cta_text': 'Open calculator',
            'hero_primary_cta_url': '/calculator/',
            'hero_secondary_cta_text': 'Request a callback',
            'hero_secondary_cta_url': '/contact/',
            'show_in_nav': True,
            'nav_order': 3,
        },
        {
            'slug': 'civil-servants',
            'navigation_label': 'Civil Servants',
            'template': WebsitePageTemplate.LANDING,
            'eyebrow': 'Civil servants',
            'hero_title': 'Designed to speak more directly to Zambia\'s dependable salaried workforce.',
            'hero_description': 'Create a focused public funnel for civil servants, teachers, nurses, and other professionals seeking a clear and respectful borrowing experience.',
            'hero_primary_cta_text': 'Estimate your repayment',
            'hero_primary_cta_url': '/calculator/',
            'hero_secondary_cta_text': 'Request a callback',
            'hero_secondary_cta_url': '/contact/',
            'show_in_nav': True,
            'nav_order': 2,
        },
        {
            'slug': 'calculator',
            'navigation_label': 'Calculator',
            'template': WebsitePageTemplate.CALCULATOR,
            'eyebrow': 'Loan calculator',
            'hero_title': 'See a repayment estimate using live LMS product settings.',
            'hero_description': 'Turn the public website into a more practical decision-support tool using live products from the LMS.',
            'hero_primary_cta_text': 'Calculate now',
            'hero_primary_cta_url': '/calculator/',
            'hero_secondary_cta_text': 'Talk to IntZam',
            'hero_secondary_cta_url': '/contact/',
            'show_in_nav': True,
            'nav_order': 5,
        },
        {
            'slug': 'contact',
            'navigation_label': 'Contact',
            'template': WebsitePageTemplate.CONTACT,
            'eyebrow': 'Contact',
            'hero_title': 'Talk to IntZam in a way that feels simple and human.',
            'hero_description': 'Use this page as the main public enquiry path for borrowers who want help before jumping into the client portal.',
            'hero_primary_cta_text': 'Request a callback',
            'hero_primary_cta_url': '/contact/',
            'hero_secondary_cta_text': 'Open calculator',
            'hero_secondary_cta_url': '/calculator/',
            'show_in_nav': True,
            'nav_order': 6,
        },
    ]

    created_pages = {}
    for page_data in page_defaults:
        slug = page_data['slug']
        page, _ = WebsitePage.objects.get_or_create(slug=slug, defaults=page_data)
        created_pages[slug] = page

    section_defaults = {
        'home': [
            {
                'title': 'Why this editor matters',
                'subtitle': 'Create richer public content without changing code.',
                'body': 'Website pages, hero copy, and modular content blocks can now be updated from Django admin.',
                'layout': WebsiteSectionLayout.CARD_GRID,
                'style': WebsiteSectionStyle.DEFAULT,
                'order': 1,
                'blocks': [
                    {'title': 'Hero copy', 'body': 'Update primary messaging and calls to action from admin.', 'badge': 'Editable', 'order': 1},
                    {'title': 'Sections', 'body': 'Publish page sections with their own layout and content.', 'badge': 'Modular', 'order': 2},
                    {'title': 'Blocks', 'body': 'Add cards, stats, quotes, and CTA-style content blocks per section.', 'badge': 'Flexible', 'order': 3},
                ],
            },
        ],
        'about': [
            {
                'title': 'What powers the website',
                'subtitle': 'A public front door connected to the LMS.',
                'body': 'Use these blocks to explain your brand, process, and operations in a way that feels more polished and up to date.',
                'layout': WebsiteSectionLayout.CARD_GRID,
                'style': WebsiteSectionStyle.DEFAULT,
                'order': 1,
                'blocks': [
                    {'title': 'Mission', 'body': 'Explain IntZam\'s lending purpose in human-centered language.', 'badge': 'Brand', 'order': 1},
                    {'title': 'Platform', 'body': 'Show how the public website connects into the LMS operations layer.', 'badge': 'Connected', 'order': 2},
                    {'title': 'Trust', 'body': 'Use editable sections for credibility, process, and borrower reassurance.', 'badge': 'Confidence', 'order': 3},
                ],
            },
        ],
        'eligibility': [
            {
                'title': 'Typical borrower readiness',
                'subtitle': 'Common eligibility themes you can explain publicly.',
                'body': 'This section can be updated as products or qualification language evolves.',
                'layout': WebsiteSectionLayout.FEATURE_LIST,
                'style': WebsiteSectionStyle.ALT,
                'order': 1,
                'blocks': [
                    {'title': 'Identity details', 'body': 'Encourage borrowers to prepare clear identification and contact details.', 'order': 1},
                    {'title': 'Income context', 'body': 'Explain the role of stable income and affordability in the assessment journey.', 'order': 2},
                    {'title': 'Product fit', 'body': 'Help visitors compare suitable products and realistic borrowing ranges.', 'order': 3},
                ],
            },
        ],
        'civil-servants': [
            {
                'title': 'Focused messaging for salaried professionals',
                'subtitle': 'A more relevant public experience for civil servants and related audiences.',
                'body': 'Update this section to test messaging for ministry staff, teachers, nurses, and other dependable earners.',
                'layout': WebsiteSectionLayout.CARD_GRID,
                'style': WebsiteSectionStyle.HIGHLIGHT,
                'order': 1,
                'blocks': [
                    {'title': 'Government officers', 'body': 'Highlight professionalism, speed, and predictable repayments.', 'badge': 'Public service', 'order': 1},
                    {'title': 'Teachers', 'body': 'Address everyday household goals in clear and calm language.', 'badge': 'Education', 'order': 2},
                    {'title': 'Nurses', 'body': 'Speak to reliability and practical financial flexibility.', 'badge': 'Healthcare', 'order': 3},
                ],
            },
        ],
        'calculator': [
            {
                'title': 'Why this calculator helps',
                'subtitle': 'A more useful public website for Zambia-focused borrowers.',
                'body': 'Show visitors what they may repay before they commit to registration or a full application.',
                'layout': WebsiteSectionLayout.STATS,
                'style': WebsiteSectionStyle.DEFAULT,
                'order': 1,
                'blocks': [
                    {'title': 'Live products', 'value': 'LMS-linked', 'body': 'Calculator ranges can reflect your real active products.', 'order': 1},
                    {'title': 'Clear estimates', 'value': 'Monthly', 'body': 'Show monthly repayment and total repayable with less friction.', 'order': 2},
                    {'title': 'Better conversion', 'value': 'Public', 'body': 'Let visitors self-qualify mentally before applying.', 'order': 3},
                ],
            },
        ],
        'contact': [
            {
                'title': 'Why reach out first',
                'subtitle': 'Create a softer path into borrowing for visitors who prefer human support.',
                'body': 'This content can help explain response times, channels, or next steps after enquiry submission.',
                'layout': WebsiteSectionLayout.TEXT,
                'style': WebsiteSectionStyle.ALT,
                'order': 1,
                'blocks': [],
            },
        ],
    }

    for slug, sections in section_defaults.items():
        page = created_pages.get(slug)
        if not page or page.sections.exists():
            continue

        for section_data in sections:
            blocks = section_data.pop('blocks', [])
            section = WebsitePageSection.objects.create(page=page, **section_data)
            for block_data in blocks:
                WebsitePageBlock.objects.create(section=section, **block_data)
