const navToggle = document.querySelector('.nav-toggle');
const nav = document.querySelector('.nav');
const navLinks = document.querySelectorAll('.nav a');
const leadForm = document.getElementById('lead-form');
const leadFormStatus = document.getElementById('lead-form-status');
const calculatorForm = document.getElementById('calculator-form');
const calculatorStatus = document.getElementById('calculator-status');
const currentPageSlug = document.body.dataset.page;

const isHttp = window.location.protocol === 'http:' || window.location.protocol === 'https:';
const apiBase = isHttp ? `${window.location.origin}/api/v1/website` : null;
const currencyFormatter = new Intl.NumberFormat('en-ZM', {
  style: 'currency',
  currency: 'ZMW',
  maximumFractionDigits: 0,
});

if (navToggle && nav) {
  navToggle.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('is-open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
  });

  navLinks.forEach((link) => {
    link.addEventListener('click', () => {
      nav.classList.remove('is-open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 }
);

function observeReveals(root = document) {
  root.querySelectorAll('.reveal').forEach((item) => observer.observe(item));
}

function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element && value !== undefined && value !== null) {
    element.textContent = value;
  }
}

function setLink(id, href, text) {
  const element = document.getElementById(id);
  if (!element) return;
  if (href) element.href = href;
  if (text) element.textContent = text;
}

function setPortalLinks(clientPortalUrl) {
  document.querySelectorAll('[data-client-link]').forEach((link) => {
    if (clientPortalUrl) link.setAttribute('href', clientPortalUrl);
  });
}

function setContactLinks(email, phone) {
  if (email) {
    document.querySelectorAll('[data-contact-email]').forEach((link) => {
      link.setAttribute('href', `mailto:${email}`);
      link.textContent = email;
    });
  }

  if (phone) {
    const tel = `tel:${String(phone).replace(/\s+/g, '')}`;
    document.querySelectorAll('[data-contact-phone]').forEach((link) => {
      link.setAttribute('href', tel);
      link.textContent = phone;
    });
  }
}

function setSocialLinks(settings) {
  const wa = document.getElementById('social-whatsapp');
  const fb = document.getElementById('social-facebook');
  const li = document.getElementById('social-linkedin');

  if (wa) {
    if (settings.whatsapp_number) {
      const num = String(settings.whatsapp_number).replace(/\s+/g, '');
      wa.href = `https://wa.me/${num.replace('+', '')}`;
      wa.style.display = '';
    } else {
      wa.style.display = 'none';
    }
  }
  if (fb) {
    if (settings.facebook_url) { fb.href = settings.facebook_url; fb.style.display = ''; }
    else { fb.style.display = 'none'; }
  }
  if (li) {
    if (settings.linkedin_url) { li.href = settings.linkedin_url; li.style.display = ''; }
    else { li.style.display = 'none'; }
  }
}

function setTrustSignals(settings) {
  const regEl = document.getElementById('trust-registration');
  const licEl = document.getElementById('trust-licence');
  const addrEl = document.getElementById('trust-address');
  const yearEl = document.getElementById('trust-year');

  if (regEl && settings.company_registration) regEl.textContent = `Reg. No. ${settings.company_registration}`;
  if (licEl && settings.regulatory_licence && settings.regulatory_body) {
    licEl.textContent = `Licensed by ${settings.regulatory_body} · Licence ${settings.regulatory_licence}`;
  }
  if (addrEl && settings.physical_address) addrEl.textContent = settings.physical_address;
  if (yearEl) yearEl.textContent = new Date().getFullYear();
}

function renderProducts(products, clientPortalUrl) {
  const grid = document.getElementById('product-grid');
  if (!grid || !Array.isArray(products) || products.length === 0) return;

  grid.innerHTML = products.slice(0, 6).map((product, index) => {
    const minAmount = Number(product.min_amount || 0);
    const maxAmount = Number(product.max_amount || 0);
    const minTerm = Number(product.min_term || 0);
    const maxTerm = Number(product.max_term || 0);

    return `
      <article class="feature-card reveal">
        <div class="feature-icon">${String(index + 1).padStart(2, '0')}</div>
        <h3>${escapeHtml(product.name)}</h3>
        <p>${escapeHtml(product.description || 'Transparent loan terms with a clean digital application experience.')}</p>
        <ul>
          <li>${escapeHtml(`${currencyFormatter.format(minAmount)} to ${currencyFormatter.format(maxAmount)}`)}</li>
          <li>${escapeHtml(`${minTerm} to ${maxTerm} months`)}</li>
          <li>${escapeHtml(`Interest rate ${Number(product.interest_rate || 0)}%`)}</li>
        </ul>
        <div class="hero-actions" style="margin-top: 18px;">
          <a class="btn btn-secondary" href="${escapeHtml(clientPortalUrl || '/client-pwa/')}">Apply for this product</a>
        </div>
      </article>
    `;
  }).join('');

  observeReveals(grid);
}

function renderAudiences(audiences) {
  const grid = document.getElementById('audience-grid');
  if (!grid || !Array.isArray(audiences) || audiences.length === 0) return;

  grid.innerHTML = audiences.map((audience) => `
    <article class="audience-card reveal">
      <div class="audience-badge">${escapeHtml(audience.badge || 'Audience')}</div>
      <h3>${escapeHtml(audience.name)}</h3>
      <p>${escapeHtml(audience.description)}</p>
    </article>
  `).join('');

  observeReveals(grid);
}

function renderTestimonials(testimonials) {
  const grid = document.getElementById('testimonial-grid');
  if (!grid || !Array.isArray(testimonials) || testimonials.length === 0) return;

  grid.innerHTML = testimonials.map((testimonial) => `
    <article class="quote-card reveal">
      <p>"${escapeHtml(testimonial.quote)}"</p>
      <strong>${escapeHtml(testimonial.name)}${testimonial.role ? `, ${escapeHtml(testimonial.role)}` : ''}</strong>
    </article>
  `).join('');

  observeReveals(grid);
}

function renderFaqs(faqs) {
  const list = document.getElementById('faq-list');
  if (!list || !Array.isArray(faqs) || faqs.length === 0) return;

  list.innerHTML = faqs.map((faq, index) => `
    <details class="faq-item reveal" ${index === 0 ? 'open' : ''}>
      <summary>${escapeHtml(faq.question)}</summary>
      <p>${escapeHtml(faq.answer)}</p>
    </details>
  `).join('');

  observeReveals(list);
}

function renderCalculatorOptions(products) {
  const select = document.getElementById('calculator-product');
  if (!select || !Array.isArray(products) || products.length === 0) return;

  select.innerHTML = products.map((product) => `
    <option value="${product.id}">${escapeHtml(product.name)} · ${currencyFormatter.format(Number(product.min_amount || 0))} - ${currencyFormatter.format(Number(product.max_amount || 0))}</option>
  `).join('');
}

function renderCalculatorResult(result) {
  const empty = document.getElementById('calculator-empty');
  const output = document.getElementById('calculator-output');
  const schedule = document.getElementById('calculator-schedule');

  if (!output || !schedule || !result) return;

  if (empty) empty.hidden = true;
  output.hidden = false;

  setText('result-product', result.product_name);
  setText('result-principal', currencyFormatter.format(Number(result.principal || 0)));
  setText('result-monthly', currencyFormatter.format(Number(result.monthly_payment || 0)));
  setText('result-total', currencyFormatter.format(Number(result.total_repayable || 0)));
  setText('result-interest', currencyFormatter.format(Number(result.total_interest || 0)));
  setText('result-rate', `${Number(result.interest_rate || 0)}%`);
  setText(
    'result-rate-breakdown',
    `Nominal ${Number(result.nominal_interest_rate || 0)}% + Credit facilitation ${Number(result.credit_facilitation_fee || 0)}% + Processing ${Number(result.processing_fee || 0)}%`
  );

  const firstMonths = Array.isArray(result.schedule) ? result.schedule.slice(0, 4) : [];
  schedule.innerHTML = firstMonths.map((item) => `
    <div class="schedule-item">
      <strong>Month ${item.month}</strong>
      <span>${currencyFormatter.format(Number(item.payment || 0))}</span>
      <span>${currencyFormatter.format(Number(item.principal || 0))} principal</span>
      <span>${currencyFormatter.format(Number(item.interest || 0))} interest</span>
    </div>
  `).join('');
}

function getPageHeroElement() {
  if (currentPageSlug === 'home') {
    return document.querySelector('.hero');
  }
  return document.querySelector('.page-hero');
}

function renderDynamicSections(sections) {
  const container = document.getElementById('dynamic-page-sections');
  if (!container || !Array.isArray(sections) || sections.length === 0) return;

  container.innerHTML = sections.map((section) => {
    const sectionClass = section.style === 'ALT'
      ? 'section section-alt'
      : section.style === 'HIGHLIGHT'
        ? 'section section-highlight'
        : 'section';

    const blocks = Array.isArray(section.blocks) ? section.blocks : [];
    const sectionMedia = section.image_url
      ? `<div class="dynamic-media reveal"><img src="${escapeHtml(section.image_url)}" alt="${escapeHtml(section.image_alt || section.title)}" /></div>`
      : '';

    let blocksHtml = '';
    if (blocks.length > 0 && section.layout === 'TEAM') {
      blocksHtml = `
        <div class="team-grid">
          ${blocks.map((block) => `
            <article class="team-card reveal">
              ${block.image_url
                ? `<div class="team-photo"><img src="${escapeHtml(block.image_url)}" alt="${escapeHtml(block.image_alt || block.title)}" /></div>`
                : `<div class="team-avatar">${escapeHtml(block.title.charAt(0).toUpperCase())}</div>`
              }
              <h3>${escapeHtml(block.title)}</h3>
              ${block.subtitle ? `<span class="team-role">${escapeHtml(block.subtitle)}</span>` : ''}
              ${block.body ? `<p>${escapeHtml(block.body)}</p>` : ''}
            </article>
          `).join('')}
        </div>
      `;
    } else if (blocks.length > 0 && section.layout === 'PHOTO_GRID') {
      blocksHtml = `
        <div class="photo-grid">
          ${blocks.map((block) => `
            <article class="photo-card reveal">
              <div class="photo-card-image">
                ${block.image_url
                  ? `<img src="${escapeHtml(block.image_url)}" alt="${escapeHtml(block.image_alt || block.title)}" />`
                  : `<span class="photo-card-image-placeholder">&#9679;</span>`
                }
              </div>
              <div class="photo-card-body">
                ${block.badge ? `<div class="photo-card-badge">${escapeHtml(block.badge)}</div>` : ''}
                <h3>${escapeHtml(block.title)}</h3>
                ${block.body ? `<p>${escapeHtml(block.body)}</p>` : ''}
              </div>
            </article>
          `).join('')}
        </div>
      `;
    } else if (blocks.length > 0) {
      blocksHtml = `
        <div class="dynamic-block-grid">
          ${blocks.map((block) => `
            <article class="dynamic-block reveal">
              ${block.badge ? `<div class="dynamic-block-badge">${escapeHtml(block.badge)}</div>` : ''}
              ${block.value ? `<div class="dynamic-block-value">${escapeHtml(block.value)}</div>` : ''}
              <h3>${escapeHtml(block.title)}</h3>
              ${block.subtitle ? `<div class="muted">${escapeHtml(block.subtitle)}</div>` : ''}
              ${block.body ? `<p>${escapeHtml(block.body)}</p>` : ''}
              ${block.image_url ? `<div class="dynamic-block-image"><img src="${escapeHtml(block.image_url)}" alt="${escapeHtml(block.image_alt || block.title)}" /></div>` : ''}
              ${block.cta_text && block.cta_url ? `<div class="link-row"><a class="btn btn-secondary" href="${escapeHtml(block.cta_url)}">${escapeHtml(block.cta_text)}</a></div>` : ''}
            </article>
          `).join('')}
        </div>
      `;
    } else if (section.body || section.cta_text) {
      blocksHtml = `
        <div class="content-card reveal">
          ${section.body ? `<p>${escapeHtml(section.body)}</p>` : ''}
          ${section.cta_text && section.cta_url ? `<div class="link-row"><a class="btn btn-secondary" href="${escapeHtml(section.cta_url)}">${escapeHtml(section.cta_text)}</a></div>` : ''}
        </div>
      `;
    }

    return `
      <section class="${sectionClass}">
        <div class="container">
          <div class="section-heading reveal">
            <h2>${escapeHtml(section.title)}</h2>
            ${section.subtitle ? `<p>${escapeHtml(section.subtitle)}</p>` : ''}
          </div>
          ${sectionMedia}
          ${blocksHtml}
        </div>
      </section>
    `;
  }).join('');

  observeReveals(container);
}

function applyPageContent(page) {
  if (!page) return;

  setText('page-eyebrow', page.eyebrow);
  setText('page-title', page.hero_title);
  setText('page-description', page.hero_description);
  setLink('page-primary-cta', page.hero_primary_cta_url, page.hero_primary_cta_text);
  setLink('page-secondary-cta', page.hero_secondary_cta_url, page.hero_secondary_cta_text);

  const heroElement = getPageHeroElement();
  if (heroElement && page.hero_image_url) {
    heroElement.style.setProperty('--page-hero-image', `url('${page.hero_image_url}')`);
    heroElement.classList.add('has-hero-image');
  }

  const sideIllustration = document.getElementById('page-side-illustration');
  if (sideIllustration && page.illustration_image_url) {
    sideIllustration.src = page.illustration_image_url;
    if (page.illustration_image_alt) {
      sideIllustration.alt = page.illustration_image_alt;
    }
  }

  if (page.seo_title) {
    document.title = page.seo_title;
  }

  renderDynamicSections(page.sections);
}

function applySettings(settings) {
  if (!settings) return;

  setText('hero-eyebrow', settings.hero_eyebrow);
  setText('hero-title', settings.hero_title);
  setText('hero-description', settings.hero_description);
  setText('zambia-focus-copy', settings.zambia_focus_copy);
  setText('audience-intro', settings.audience_intro);
  setText('lead-form-title', settings.lead_form_title);
  setText('lead-form-description', settings.lead_form_description);

  setLink('primary-cta', settings.hero_primary_cta_url, settings.hero_primary_cta_text);
  setLink('secondary-cta', settings.hero_secondary_cta_url, settings.hero_secondary_cta_text);

  setPortalLinks(settings.client_portal_url);
  setContactLinks(settings.contact_email, settings.contact_phone);
  setSocialLinks(settings);
  setTrustSignals(settings);

  if (settings.site_name && settings.site_tagline && document.body.dataset.page !== 'calculator') {
    document.title = `${settings.site_name} | ${settings.site_tagline}`;
  }
}

function extractErrorMessage(payload) {
  if (!payload) return 'Something went wrong. Please try again.';
  if (typeof payload.error === 'string') return payload.error;

  const firstEntry = Object.values(payload)[0];
  if (Array.isArray(firstEntry) && firstEntry.length > 0) return String(firstEntry[0]);
  if (typeof firstEntry === 'string') return firstEntry;

  return 'Something went wrong. Please try again.';
}

async function loadWebsiteContent() {
  if (!apiBase) return null;

  try {
    const response = await fetch(`${apiBase}/content/`, {
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) return null;

    const payload = await response.json();
    applySettings(payload.settings);
    renderProducts(payload.products, payload.settings?.client_portal_url);
    renderAudiences(payload.audiences);
    renderTestimonials(payload.testimonials);
    renderFaqs(payload.faqs);
    renderCalculatorOptions(payload.products);
    return payload;
  } catch {
    return null;
  }
}

async function loadCurrentPageContent() {
  if (!apiBase || !currentPageSlug) return null;

  try {
    const response = await fetch(`${apiBase}/pages/${currentPageSlug}/`, {
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) return null;

    const page = await response.json();
    applyPageContent(page);
    return page;
  } catch {
    return null;
  }
}

async function submitLeadForm(event) {
  event.preventDefault();
  if (!leadForm || !leadFormStatus) return;

  if (!apiBase) {
    leadFormStatus.textContent = 'Lead capture is available when the website is served through the Django backend.';
    leadFormStatus.className = 'form-status status-error';
    return;
  }

  const formData = new FormData(leadForm);
  const payload = Object.fromEntries(formData.entries());
  payload.consent = formData.get('consent') === 'true';
  payload.source_page = window.location.pathname;

  if (!payload.desired_amount) {
    delete payload.desired_amount;
  }

  leadFormStatus.textContent = 'Submitting your enquiry...';
  leadFormStatus.className = 'form-status';

  try {
    const response = await fetch(`${apiBase}/leads/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const responseData = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw responseData;
    }

    leadForm.reset();
    leadFormStatus.textContent = 'Thank you. An IntZam team member will contact you shortly.';
    leadFormStatus.className = 'form-status status-success';
  } catch (errorPayload) {
    leadFormStatus.textContent = extractErrorMessage(errorPayload);
    leadFormStatus.className = 'form-status status-error';
  }
}

async function submitCalculator(event) {
  event.preventDefault();
  if (!calculatorForm || !calculatorStatus) return;

  if (!apiBase) {
    calculatorStatus.textContent = 'Calculator is available when the website is served through the Django backend.';
    calculatorStatus.className = 'form-status status-error';
    return;
  }

  const formData = new FormData(calculatorForm);
  const payload = {
    product_id: formData.get('product_id'),
    principal: formData.get('principal'),
    term_months: formData.get('term_months'),
  };

  calculatorStatus.textContent = 'Calculating estimate...';
  calculatorStatus.className = 'form-status';

  try {
    const response = await fetch(`${apiBase}/calculator/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw result;

    renderCalculatorResult(result);
    calculatorStatus.textContent = 'Estimate updated from your website product configuration.';
    calculatorStatus.className = 'form-status status-success';
  } catch (errorPayload) {
    calculatorStatus.textContent = extractErrorMessage(errorPayload);
    calculatorStatus.className = 'form-status status-error';
  }
}

observeReveals();
loadWebsiteContent();
loadCurrentPageContent();

if (leadForm) {
  leadForm.addEventListener('submit', submitLeadForm);
}

if (calculatorForm) {
  calculatorForm.addEventListener('submit', submitCalculator);
}
