/* SeQontrol site chrome. No dependencies, no network calls.
   Three jobs: the mobile nav, the current-page nav marker, and the footer year. */
(function () {
  'use strict';

  // --- mobile nav -----------------------------------------------------------
  var toggle = document.querySelector('.nav-toggle');
  var links = document.getElementById('nav-links');

  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });

    // Close on navigation. Most menu entries load a new document, which closes the panel for free —
    // but four do not. build_nav.py emits the unreleased products as coming.html#dredd and friends,
    // so on products/coming.html itself those are same-document jumps: nothing unloads, the target
    // scrolls to just under the header, and the still-open opaque panel covers it. Half the product
    // menu read as dead links on the one page that describes those products.
    links.addEventListener('click', function (e) {
      // Only close when the click is actually going to navigate this document. A middle-click or a
      // Ctrl/Cmd/Shift/Alt-click opens a new tab and leaves this page exactly where it was, so
      // closing the panel would make the menu vanish with nothing having visibly happened - and at
      // this breakpoint the open class is the only thing rendering it.
      if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.defaultPrevented) return;
      var el = e.target;
      while (el && el !== links && el.tagName !== 'A') el = el.parentNode;
      if (!el || el.tagName !== 'A') return;
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });

    // Close on Escape so keyboard users are not trapped behind the panel.
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && links.classList.contains('open')) {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
      }
    });
  }

  // --- current page ---------------------------------------------------------
  // Marks the nav entry for the page you are on, by comparing whole resolved
  // paths. The previous version compared only the last path segment, which is
  // how the home page came to light up Guides: "/" resolves to index.html, and
  // the Guides link is guides/index.html, whose last segment is index.html too.
  // Products escaped that only because of a string test for "products/" - and
  // the same shortcut meant /guides/ never marked itself, since there the last
  // segment is "guides" and no nav href ends in it.
  //
  // a.pathname is the href already resolved against this page, so a link one
  // directory down is compared the way the browser would follow it.

  // One spelling per page: a directory index is the directory, a directory
  // carries its trailing slash, and a page keeps its .html.
  function canon(p) {
    p = p.replace(/\/index\.html$/, '/');
    var last = p.substring(p.lastIndexOf('/') + 1);
    if (last && last.indexOf('.') === -1) p += '/';
    return p || '/';
  }

  var here = canon(window.location.pathname);

  Array.prototype.forEach.call(document.querySelectorAll('.nav-links a'), function (a) {
    if (a.classList.contains('btn')) return;
    var target = canon(a.pathname);
    // A section index owns the pages beneath it, so a product page marks
    // Products and a guide marks Guides. Excluding '/' stops a home link, if
    // one is ever added, from owning the whole site.
    var owns = target !== '/' && target.charAt(target.length - 1) === '/' &&
               here.indexOf(target) === 0;

    if (here === target || owns) {
      a.setAttribute('aria-current', 'page');
    }
  });

  // --- footer year ----------------------------------------------------------
  Array.prototype.forEach.call(document.querySelectorAll('[data-year]'), function (el) {
    el.textContent = String(new Date().getFullYear());
  });

  // --- audience doors (home page) -------------------------------------------
  // Progressive, like the tabs below. The markup ships two plain links (#estate, #fleet) and both
  // audience sections visible, so without JavaScript each door is an in-page jump and nothing is
  // hidden. Here they become a switch: the chosen door is marked aria-current and every element
  // carrying the other door's data-door-panel is hidden - the section under the hero and the
  // closing call-to-action alike. [data-doors-ready] goes on <html> because the panels are not
  // inside the doors' container, and print CSS keys off it to show both on paper.
  var doorRoot = document.querySelector('[data-doors]');
  if (doorRoot) {
    var doors = [].slice.call(doorRoot.querySelectorAll('[data-door]'));
    var doorPanels = [].slice.call(document.querySelectorAll('[data-door-panel]'));
    var pickDoor = function (name) {
      doors.forEach(function (d) {
        d.setAttribute('aria-current', d.getAttribute('data-door') === name ? 'true' : 'false');
      });
      doorPanels.forEach(function (p) { p.hidden = p.getAttribute('data-door-panel') !== name; });
    };
    doors.forEach(function (d) {
      d.addEventListener('click', function (e) {
        // A modified click opens a new tab; leave that to the browser.
        if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        var name = d.getAttribute('data-door');
        pickDoor(name);
        // Keep the choice in the address so a shared link opens the same door. replaceState, not a
        // hash assignment, because assigning the hash would jump the page to the section.
        if (window.history && history.replaceState) history.replaceState(null, '', '#' + name);
      });
    });
    document.documentElement.setAttribute('data-doors-ready', '');
    var wantDoor = window.location.hash.replace('#', '');
    pickDoor(doors.some(function (d) { return d.getAttribute('data-door') === wantDoor; })
      ? wantDoor : doors[0].getAttribute('data-door'));
  }

  // --- product carousel (home page) -------------------------------------------
  // Progressive, like the tabs below: the markup ships every slide visible and the controls hidden.
  // Here the slides become one-at-a-time. Inactive slides are hidden with visibility rather than
  // [hidden] so they keep their place in the shared grid cell and the box never changes height.
  //
  // Automatic rotation, with the limits that make it acceptable (WCAG 2.2.2 among them):
  //  - one slide every INTERVAL ms, only while the carousel is on screen and the tab is visible;
  //  - one round only: it stops when it is back on the first slide;
  //  - a visible pause/play button, and a progress line so the change is never a surprise;
  //  - any click, touch, hover or keyboard focus inside the carousel stops it for good, unless the
  //    visitor pressed play themselves, in which case only the controls stop it;
  //  - never starts on its own for visitors who ask their system for reduced motion.
  Array.prototype.forEach.call(document.querySelectorAll('[data-carousel]'), function (root) {
    var tabs = [].slice.call(root.querySelectorAll('[role="tab"]'));
    var slides = [].slice.call(root.querySelectorAll('[role="tabpanel"]'));
    var count = root.querySelector('.carousel-count');
    var playBtn = root.querySelector('[data-carousel-play]');
    var progress = root.querySelector('.carousel-progress');
    var slideBox = root.querySelector('.carousel-slides');
    if (!tabs.length || tabs.length !== slides.length) return;

    var INTERVAL = 10000;
    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var current = 0;
    var playing = !reduced;     // rotation wanted
    var chosen = false;         // the visitor pressed play themselves
    var inView = false;
    var timer = null;
    var advanced = 0;           // slides moved by the timer in this round

    if (progress) progress.style.setProperty('--carousel-interval', INTERVAL + 'ms');

    function show(index, moveFocus) {
      current = (index + slides.length) % slides.length;
      tabs.forEach(function (tab, i) {
        var on = i === current;
        tab.setAttribute('aria-selected', String(on));
        tab.setAttribute('tabindex', on ? '0' : '-1');
        if (on) { slides[i].removeAttribute('data-inactive'); slides[i].removeAttribute('aria-hidden'); }
        else { slides[i].setAttribute('data-inactive', ''); slides[i].setAttribute('aria-hidden', 'true'); }
        // Keep focusable content in hidden slides out of the tab order.
        [].forEach.call(slides[i].querySelectorAll('a, [tabindex]'), function (el) {
          if (on) {
            if (el.hasAttribute('data-carousel-tabindex')) {
              el.setAttribute('tabindex', el.getAttribute('data-carousel-tabindex'));
              el.removeAttribute('data-carousel-tabindex');
            } else if (el.getAttribute('tabindex') === '-1' && el.tagName === 'A') {
              el.removeAttribute('tabindex');
            }
          } else {
            if (el.hasAttribute('tabindex') && !el.hasAttribute('data-carousel-tabindex')) {
              el.setAttribute('data-carousel-tabindex', el.getAttribute('tabindex'));
            }
            el.setAttribute('tabindex', '-1');
          }
        });
      });
      if (count) count.textContent = (current + 1) + ' / ' + slides.length;
      if (moveFocus) tabs[current].focus();
    }

    function running() { return playing && inView && !document.hidden; }

    // (Re)start the clock for the slide on screen, or stop it. Called after every state change.
    function schedule() {
      clearTimeout(timer);
      timer = null;
      if (progress) {
        progress.removeAttribute('data-run');
        void progress.offsetWidth;   // restart the fill from empty
      }
      if (playBtn) {
        if (playing) playBtn.removeAttribute('data-paused'); else playBtn.setAttribute('data-paused', '');
        playBtn.setAttribute('aria-label', playing ? 'Pause automatic rotation' : 'Start automatic rotation');
      }
      // Screen readers: announce slide changes only when a person caused them.
      if (slideBox) slideBox.setAttribute('aria-live', playing ? 'off' : 'polite');
      if (!running()) return;
      if (progress) progress.setAttribute('data-run', '');
      timer = setTimeout(function () {
        show(current + 1);
        advanced += 1;
        if (current === 0 && advanced >= slides.length) playing = false;   // one round, then rest
        schedule();
      }, INTERVAL);
    }

    function stop() {
      if (!playing && !timer) return;
      playing = false;
      schedule();
    }

    tabs.forEach(function (tab, i) {
      tab.addEventListener('click', function () { show(i); stop(); });
      tab.addEventListener('keydown', function (e) {
        var next = null;
        if (e.key === 'ArrowRight') next = i + 1;
        else if (e.key === 'ArrowLeft') next = i - 1;
        else if (e.key === 'Home') next = 0;
        else if (e.key === 'End') next = tabs.length - 1;
        if (next === null) return;
        e.preventDefault();
        show(next, true);
        stop();
      });
    });
    [].forEach.call(root.querySelectorAll('[data-carousel-step]'), function (btn) {
      btn.addEventListener('click', function () {
        show(current + parseInt(btn.getAttribute('data-carousel-step'), 10));
        stop();
      });
    });
    if (playBtn) {
      playBtn.addEventListener('click', function () {
        if (playing) { stop(); return; }
        playing = true;
        chosen = true;
        advanced = 0;
        schedule();
      });
    }

    // Interest in the carousel ends the rotation, unless the visitor asked for it with play.
    function interest(e) {
      if (chosen || !playing) return;
      if (playBtn && e && e.target && playBtn.contains(e.target)) return;
      stop();
    }
    root.addEventListener('mouseenter', interest);
    root.addEventListener('focusin', interest);
    root.addEventListener('touchstart', interest, { passive: true });
    root.addEventListener('pointerdown', interest);

    document.addEventListener('visibilitychange', schedule);
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        inView = entries[0].isIntersecting;
        schedule();
      }, { threshold: 0.5 }).observe(root);
    } else {
      inView = true;
    }

    root.setAttribute('data-carousel-ready', '');
    show(0);
    schedule();
  });

  // --- pricing calculator (pricing.html) --------------------------------------
  // The markup is generated by build_legal.py; the figures come from the JSON block #calc-data, which
  // is tools/prices.py CALCULATOR. Nothing in here carries a price of its own, and verify.py fails the
  // build if a figure in that block is not printed in the tables on the same page.
  Array.prototype.forEach.call(document.querySelectorAll('[data-calculator]'), function (root) {
    var dataEl = document.getElementById('calc-data');
    var app = root.querySelector('.calc-app');
    if (!dataEl || !app) return;
    var P;
    try { P = JSON.parse(dataEl.textContent); } catch (e) { return; }

    var $ = function (sel) { return root.querySelector(sel); };
    var $$ = function (sel) { return [].slice.call(root.querySelectorAll(sel)); };
    var contact = root.getAttribute('data-contact') || '';
    var step = 1;
    var TIER = { vis: 'Visibility', gov: 'Governance', auto: 'Automation' };

    function eur(n) {
      var r = Math.round(n * 100) / 100;
      var whole = Math.floor(r);
      var cents = Math.round((r - whole) * 100);
      return '€' + whole.toLocaleString('en') + (cents ? '.' + (cents < 10 ? '0' : '') + cents : '');
    }
    function num(id) {
      var el = document.getElementById(id);
      var n = el ? parseInt(el.value, 10) : 0;
      return isNaN(n) || n < 0 ? 0 : n;
    }
    function picked(name) {
      var el = root.querySelector('input[name="' + name + '"]:checked');
      return el ? el.value : null;
    }
    function on(key) {
      var el = root.querySelector('input[name="calc-p-' + key + '"]');
      return !!(el && el.checked);
    }
    function lookup(path) {
      return path.split('.').reduce(function (o, k) { return o == null ? o : o[k]; }, P);
    }

    // Prices shown in the tier pills, from the same data.
    $$('[data-price]').forEach(function (el) {
      var v = lookup(el.getAttribute('data-price'));
      if (typeof v === 'number') el.textContent = eur(v) + (el.getAttribute('data-suffix') || '');
    });

    // Starting tiers: the ones we would recommend first, and say why in the card.
    var START = { sharecare: 'gov', mailtrust: 'gov', webscan: 'free', compliance: '1', condaccess: 'gov' };
    Object.keys(START).forEach(function (k) {
      var el = root.querySelector('input[name="calc-tier-' + k + '"][value="' + START[k] + '"]');
      if (el) el.checked = true;
    });

    var WHY = {
      sharecare: {
        vis: ['Visibility:', 'read-only inventory of sharing and permissions, risk scoring and daily scans. Org-wide link and company-wide group detection is not in this tier.'],
        gov: ['Why Governance:', 'the Copilot question needs the oversharing detections (org-wide links, company-wide groups), which start here, with access reviews and waivers that expire.'],
        auto: ['Automation:', 'adds hourly scans and OneDrive permission and sharing-link write-back with undo, behind a separate remediation consent.']
      },
      mailtrust: {
        vis: ['Visibility:', 'posture for SPF, DKIM, DMARC, BIMI and MTA-STS, and the real sender inventory from aggregate reports.'],
        gov: ['Why Governance:', 'the guided staged rollout from monitoring to enforcement starts here; Visibility shows the senders but does not walk you to p=reject.'],
        auto: ['Automation:', 'writes the DNS records for you, live for Azure DNS and DNSimple only. Anywhere else you get the exact records to apply.']
      },
      condaccess: {
        vis: ['Visibility:', 'inventory of every policy and the access map.'],
        gov: ['Governance:', 'adds baseline coverage gaps and policy-as-code drift detection.'],
        auto: ['Automation:', 'adds approval-gated policy write-back.']
      },
      webscan: {
        free: ['Free:', 'the complete check set, one URL at a time, with nothing kept after the scan. Pick Pro to keep history and schedule scans.'],
        pro: ['Pro:', 'keeps results and history, scans on a schedule and alerts on expiry, new assets and regressions. Counted per monitored site.']
      }
    };

    function calc() {
      var multi = picked('calc-aud') === 'multi';
      var U = num('calc-users');
      var T = multi ? Math.max(1, num('calc-tenants')) : 1;
      var sites = num('calc-sites'), sending = num('calc-sending'), parked = num('calc-parked');
      var partner = multi && T >= P.mailtrust.partner.min_tenants;
      var lines = [], later = [];
      var t;

      if (on('sharecare')) {
        t = picked('calc-tier-sharecare') || 'gov';
        var rate = P.sharecare.tiers[t], disc = 0;
        P.sharecare.volume.forEach(function (b) { if (!disc && U > b[0]) disc = b[1]; });
        lines.push({ name: 'ShareCare', tier: TIER[t], qty: U.toLocaleString('en') + ' users', rate: eur(rate) + ' / user',
          note: disc ? disc + '% volume discount on the whole line' + (multi ? ', counted across your book' : '') : 'No seat minimum',
          value: U * rate * (100 - disc) / 100 });
      }
      if (on('security')) {
        var sr = on('sharecare') ? P.security.with_sharecare : P.security.standalone;
        var perUser = U * sr, floor = T * P.security.tenant_min;
        lines.push({ name: 'SecurityPortal', tier: 'One tier', qty: U.toLocaleString('en') + ' users' + (multi ? ', ' + T + ' tenants' : ''),
          rate: eur(sr) + ' / user ' + (on('sharecare') ? '(with ShareCare)' : '(standalone)'),
          note: eur(P.security.tenant_min) + ' per tenant minimum' + (floor > perUser ? ' applies' : ', not reached'),
          value: Math.max(perUser, floor) });
      }
      if (on('webscan')) {
        var pro = picked('calc-tier-webscan') === 'pro';
        lines.push({ name: 'WebScan', tier: pro ? 'Pro' : 'Free', qty: pro ? sites + ' sites' : 'One URL at a time',
          rate: pro ? eur(P.webscan.pro) + ' / site' : 'Free with every account',
          note: pro ? 'Discovered subdomains are listed free' : 'Nothing kept after the scan',
          value: pro ? sites * P.webscan.pro : 0 });
      }
      if (on('mailtrust')) {
        t = picked('calc-tier-mailtrust') || 'gov';
        var mt = partner ? P.mailtrust.partner : P.mailtrust;
        var included = P.mailtrust.parked_included * sending;
        var extra = Math.max(0, parked - included);
        lines.push({ name: 'MailTrust', tier: TIER[t] + (partner ? ', partner rate' : ''), qty: sending + ' sending, ' + parked + ' parked',
          rate: eur(mt.tiers[t]) + ' / sending domain',
          note: Math.min(parked, included) + ' parked included' + (extra ? ', ' + extra + ' at ' + eur(mt.parked) : '') +
            (multi && !partner ? '. Partner rates start at ' + P.mailtrust.partner.min_tenants + ' tenants' : ''),
          value: sending * mt.tiers[t] + extra * mt.parked });
      }
      var own = root.querySelector('input[name="calc-own"]');
      if (multi && own && own.checked) {
        lines.push({ name: 'Your own tenant', tier: 'Every released product, up to ' + P.own_tenant.max_users + ' users', qty: '1 tenant',
          rate: eur(P.own_tenant.price) + ' flat', note: 'Partner benefit, not resellable', value: P.own_tenant.price });
      }
      if (on('compliance')) {
        var fw = picked('calc-tier-compliance') || '1';
        var att = !!root.querySelector('input[name="calc-attested"]:checked');
        var fwLabel = fw === 'all' ? 'Unlimited frameworks' : fw + (fw === '1' ? ' framework' : ' frameworks');
        var cp = P.compliance.partner, cv, crate, cnote;
        if (multi && T >= cp.min_tenants) {
          var lic = fw === 'all' ? cp.all : Math.min(cp.all, cp.framework * parseInt(fw, 10));
          var perT = cp.per_tenant[att ? 'attested' : 'evidence'];
          cv = lic + T * perT; crate = eur(lic) + ' licence + ' + eur(perT) + ' / tenant'; cnote = 'Pooled framework licence across your book';
        } else {
          var band = P.compliance.bands[fw][att ? 1 : 0];
          cv = T * band; crate = eur(band) + ' / tenant'; cnote = 'Per tenant, banded by frameworks in scope';
        }
        later.push({ name: 'CompliancePortal', tier: fwLabel + ', ' + (att ? 'Attested' : 'Evidence'), qty: T + (T === 1 ? ' tenant' : ' tenants'), rate: crate, note: cnote, value: cv });
      }
      if (on('condaccess')) {
        t = picked('calc-tier-condaccess') || 'gov';
        var cr = P.condaccess.tiers[t], cu = U * cr, cf = T * P.condaccess.tenant_min;
        later.push({ name: 'ConditionalAccessPortal', tier: TIER[t], qty: U.toLocaleString('en') + ' users', rate: eur(cr) + ' / user',
          note: eur(P.condaccess.tenant_min) + ' per tenant minimum' + (cf > cu ? ' applies' : ', not reached'), value: Math.max(cu, cf) });
      }
      var sum = function (a) { return a.reduce(function (x, l) { return x + l.value; }, 0); };
      return { multi: multi, partner: partner, T: T, U: U, sending: sending, lines: lines, later: later, total: sum(lines), laterTotal: sum(later) };
    }

    function cell(text, cls, small) {
      var td = document.createElement('td');
      if (cls) td.className = cls;
      td.textContent = text;
      if (small) { var s = document.createElement('small'); s.textContent = small; td.appendChild(s); }
      return td;
    }
    function fillTable(tbody, rows) {
      tbody.textContent = '';
      rows.forEach(function (l) {
        var tr = document.createElement('tr');
        tr.appendChild(cell(l.name, '', l.tier));
        tr.appendChild(cell(l.qty));
        tr.appendChild(cell(l.rate, '', l.note));
        tr.appendChild(cell(eur(l.value), 'num'));
        tbody.appendChild(tr);
      });
    }
    function out(name) { return $$('[data-out="' + name + '"]'); }
    function setText(name, text) { out(name).forEach(function (el) { el.textContent = text; }); }

    function asText(c) {
      var d = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
      var rows = ['SeQontrol estimate, ' + d, basis(c), ''];
      c.lines.forEach(function (l) { rows.push(l.name + ' (' + l.tier + '): ' + l.qty + ', ' + l.rate + ' = ' + eur(l.value) + ' per month'); });
      rows.push('', 'Per month, excluding VAT: ' + eur(c.total), 'Per year: ' + eur(c.total * 12));
      if (c.later.length) {
        rows.push('', 'On release, not in the total:');
        c.later.forEach(function (l) { rows.push(l.name + ' (' + l.tier + '): ' + eur(l.value) + ' per month'); });
      }
      rows.push('', ($('#calc-disclaimer') || {}).textContent || '', 'Calculated on https://seqontrol.com/pricing.html');
      return rows.join('\r\n');
    }
    function basis(c) {
      return c.multi ? 'Provider pricing, pooled across ' + c.T + ' tenants. Euros, excluding VAT. Sold to businesses only.'
        : 'Retail pricing for one environment. Euros, excluding VAT. Sold to businesses only.';
    }

    function render() {
      var c = calc();
      if (c.multi) root.setAttribute('data-multi', ''); else root.removeAttribute('data-multi');
      $$('.calc-product').forEach(function (card) {
        var key = card.getAttribute('data-product');
        if (on(key)) card.setAttribute('data-on', ''); else card.removeAttribute('data-on');
        var why = card.querySelector('[data-why]');
        if (!why) return;
        var w = null;
        if (WHY[key]) w = WHY[key][picked('calc-tier-' + key) || START[key]];
        if (key === 'security') w = ['One tier:', (on('sharecare') ? eur(P.security.with_sharecare) + ' per user because ShareCare is selected (' + eur(P.security.standalone) + ' on its own)' : eur(P.security.standalone) + ' per user on its own (' + eur(P.security.with_sharecare) + ' with any ShareCare tier)') + ', with a ' + eur(P.security.tenant_min) + ' monthly minimum per tenant. Scan-only; it never writes.'];
        if (key === 'compliance') w = ['Not on sale yet:', 'built and running, so it is shown as an on-release figure outside the total. Technical control evidence, not a whole-company compliance programme.'];
        why.textContent = '';
        if (w) { var b = document.createElement('b'); b.textContent = w[0] + ' '; why.appendChild(b); why.appendChild(document.createTextNode(w[1])); }
      });
      var usersLabel = root.querySelector('label[for="calc-users"]');
      if (usersLabel) usersLabel.textContent = c.multi ? 'Users across all client tenants' : 'Microsoft 365 users';
      var usersHint = document.getElementById('calc-users');
      if (usersHint && usersHint.parentNode.querySelector('.hint')) {
        usersHint.parentNode.querySelector('.hint').textContent = c.multi ? 'Pooled: volume bands count your whole book, not each client.' : 'Licensed users in the tenant.';
      }

      var errs = [];
      if (c.multi && num('calc-tenants') < 1) errs.push('Add at least one client tenant.');
      if (on('mailtrust') && c.sending < 1) errs.push('MailTrust is counted on sending domains: add at least one, or remove MailTrust in step 3.');
      var err = $('.calc-error');
      if (err) { err.textContent = errs.join(' '); err.hidden = !errs.length; }

      out('lines').forEach(function (tb) { fillTable(tb, c.lines); });
      out('later').forEach(function (tb) { fillTable(tb, c.later); });
      var laterBox = $('.calc-later');
      if (laterBox) laterBox.hidden = !c.later.length;
      setText('monthly', eur(c.total));
      setText('annual', eur(c.total * 12));
      setText('basis', basis(c));
      setText('intro', c.multi
        ? (c.partner ? 'Provider pricing for ' + c.T + ' managed tenants: users, sites and domains pooled across your book, partner rates where they exist.'
                     : 'Provider pricing for ' + c.T + ' tenants, pooled across your book. Partner rates for MailTrust and pooled compliance start at ten managed tenants.')
        : 'Retail prices for one Microsoft 365 environment.');
      out('summary').forEach(function (ul) {
        ul.textContent = '';
        if (!c.lines.length) {
          var li0 = document.createElement('li'); li0.textContent = 'Pick what you need in step 3 and the total builds here.'; ul.appendChild(li0);
        }
        c.lines.forEach(function (l) {
          var li = document.createElement('li');
          var a = document.createElement('span'); a.textContent = l.name;
          var b = document.createElement('span'); b.textContent = eur(l.value);
          li.appendChild(a); li.appendChild(b); ul.appendChild(li);
        });
      });
      out('laternote').forEach(function (el) {
        el.hidden = !c.later.length;
        el.textContent = 'Plus ' + eur(c.laterTotal) + ' a month on release for products not on sale yet. Not in the total.';
      });
      var mail = root.querySelector('[data-act="mail"]');
      if (mail && contact) {
        mail.href = 'mailto:' + contact + '?subject=' + encodeURIComponent('Question about my estimate') +
          '&body=' + encodeURIComponent(asText(c) + '\r\n\r\nMy question:\r\n');
      }
      return c;
    }

    function show(n, focus) {
      step = Math.max(1, Math.min(5, n));
      $$('.calc-panel').forEach(function (p) { p.hidden = parseInt(p.getAttribute('data-step'), 10) !== step; });
      $$('[data-goto]').forEach(function (b) {
        if (parseInt(b.getAttribute('data-goto'), 10) === step) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
      });
      var back = root.querySelector('[data-nav="back"]'), next = root.querySelector('[data-nav="next"]');
      if (back) back.hidden = step === 1;
      if (next) {
        next.hidden = step === 5;
        next.textContent = step === 3 ? 'See the estimate' : step === 4 ? 'Keep a copy (optional)' : 'Next';
      }
      if (focus) {
        var top = root.getBoundingClientRect().top;
        if (top < 0) root.scrollIntoView({ block: 'start' });
        var panel = root.querySelector('.calc-panel[data-step="' + step + '"]');
        var target = panel && panel.querySelector('legend, h3');
        if (target) { target.setAttribute('tabindex', '-1'); target.focus({ preventScroll: true }); }
      }
    }

    $$('[data-goto]').forEach(function (b) {
      b.addEventListener('click', function () { show(parseInt(b.getAttribute('data-goto'), 10), true); });
    });
    root.addEventListener('click', function (e) {
      var nav = e.target.closest && e.target.closest('[data-nav]');
      if (nav) show(step + (nav.getAttribute('data-nav') === 'next' ? 1 : -1), true);
    });
    root.addEventListener('input', render);
    root.addEventListener('change', render);

    var printBtn = root.querySelector('[data-act="print"]');
    if (printBtn) printBtn.addEventListener('click', function () {
      var c = render();
      var sheet = document.getElementById('calc-print');
      if (!sheet) { sheet = document.createElement('div'); sheet.id = 'calc-print'; document.body.appendChild(sheet); }
      sheet.textContent = '';
      var h = document.createElement('h1'); h.textContent = 'SeQontrol estimate'; sheet.appendChild(h);
      var meta = document.createElement('p');
      meta.textContent = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) + '. ' + basis(c);
      sheet.appendChild(meta);
      var table = root.querySelector('.calc-panel[data-step="4"] .calc-table');
      if (table) sheet.appendChild(table.cloneNode(true));
      if (c.later.length) {
        var lh = document.createElement('h2'); lh.textContent = 'On release, not in the total'; sheet.appendChild(lh);
        var lt = root.querySelector('.calc-later .calc-table');
        if (lt) sheet.appendChild(lt.cloneNode(true));
      }
      var disc = $('#calc-disclaimer');
      if (disc) sheet.appendChild(disc.cloneNode(true)).removeAttribute('id');
      var src = document.createElement('p'); src.textContent = 'Calculated on https://seqontrol.com/pricing.html'; sheet.appendChild(src);
      document.documentElement.setAttribute('data-print-estimate', '');
      var done = function () { document.documentElement.removeAttribute('data-print-estimate'); window.removeEventListener('afterprint', done); };
      window.addEventListener('afterprint', done);
      window.print();
      setTimeout(done, 1000);
    });

    var copyBtn = root.querySelector('[data-act="copy"]');
    if (copyBtn) copyBtn.addEventListener('click', function () {
      var text = asText(render());
      var said = function (msg) { setText('copied', msg); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { said('Copied. Paste it wherever you need it.'); },
          function () { said('Your browser did not allow copying. Use Print or save as PDF instead.'); });
      } else {
        var ta = document.createElement('textarea');
        ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'absolute'; ta.style.left = '-9999px';
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); said('Copied. Paste it wherever you need it.'); } catch (e2) { said('Your browser did not allow copying. Use Print or save as PDF instead.'); }
        document.body.removeChild(ta);
      }
    });

    app.hidden = false;
    root.setAttribute('data-calc-ready', '');
    render();
    show(1, false);
  });

  // --- tabs -----------------------------------------------------------------
  // Progressive: the markup ships with every panel visible and the tab strip
  // hidden by CSS. Only once this runs does the container get
  // [data-tabs-ready], which reveals the strip and lets us collapse the panels.
  // No script, no loss of content.
  Array.prototype.forEach.call(document.querySelectorAll('[data-tabs]'), function (root) {
    var tabs = [].slice.call(root.querySelectorAll('[role="tab"]'));
    var panels = [].slice.call(root.querySelectorAll('[role="tabpanel"]'));
    if (!tabs.length || tabs.length !== panels.length) return;

    function select(index, moveFocus) {
      tabs.forEach(function (tab, i) {
        var on = i === index;
        tab.setAttribute('aria-selected', String(on));
        tab.setAttribute('tabindex', on ? '0' : '-1');
        panels[i].hidden = !on;
      });
      if (moveFocus) tabs[index].focus();
    }

    tabs.forEach(function (tab, i) {
      tab.addEventListener('click', function () { select(i); });
      // Both axes are accepted. The set is a vertical rail on wide screens and
      // a wrapping row on narrow ones, so neither pair of arrows is "the wrong
      // one" — declaring a fixed aria-orientation would be wrong half the time.
      tab.addEventListener('keydown', function (e) {
        var next = null;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (i + 1) % tabs.length;
        else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = (i - 1 + tabs.length) % tabs.length;
        else if (e.key === 'Home') next = 0;
        else if (e.key === 'End') next = tabs.length - 1;
        if (next === null) return;
        e.preventDefault();
        select(next, true);
      });
    });

    root.setAttribute('data-tabs-ready', '');

    // Deep links: /licensing.html#mailtrust opens that product's tab.
    var wanted = window.location.hash.replace('#', '');
    var start = 0;
    var deep = false;
    panels.forEach(function (panel, i) {
      if (panel.id === 'panel-' + wanted) { start = i; deep = true; }
    });
    select(start);
    // The hash names a panel, not an element the browser can find, so nothing
    // scrolled. On the pricing page the tabs sit well below the fold.
    if (deep) root.scrollIntoView({ block: 'start' });
  });
})();

/* ---------------------------------------------------------------- contact form
   Moved here from six inline <script> blocks on 2026-08-21. It was identical on
   every page carrying a form, so the same 2.7 KB shipped six times — and an
   inline script is the one thing that forces 'unsafe-inline' into a Content
   Security Policy. Out here it is cached once and script-src can be 'self'.

   It already guarded on the form's absence, so it is safe on every page. */
/* Same behaviour as the contact page: post when an endpoint is configured,
   otherwise compose a mailto and surface the text so a failed handoff is
   recoverable rather than silent. */
(function () {
  'use strict';
  var form = document.getElementById('contact-form');
  if (!form) return;
  var status = document.getElementById('cf-status');
  var thanks = document.getElementById('cf-thanks');
  var fallback = document.getElementById('cf-fallback');
  var submit = document.getElementById('cf-submit');
  var endpoint = (form.getAttribute('data-endpoint') || '').trim();
  // Stamped onto the form by build_nav.py from build_legal.CONTACT, so the address is written
  // down once. This was a literal '{contact}' -- a Python .format() placeholder that came along
  // when the handler moved out of the generated inline scripts, leaving every fallback mailto
  // pointing at the string "mailto:{contact}" instead of an address.
  var contact = (form.getAttribute('data-contact') || '').trim();

  function say(m) { status.textContent = m; }

  // ?topic=<key> preselects the matching <option data-topic="key">, so a "Tell me when it ships"
  // button on a product page lands on a form that already says what it is about. An unknown key,
  // or a page whose topic is a hidden input rather than a select, leaves the form as it was.
  var topicSelect = form.querySelector('select[name="topic"]');
  var wantTopic = (new URLSearchParams(window.location.search).get('topic') || '').toLowerCase();
  if (topicSelect && wantTopic) {
    Array.prototype.forEach.call(topicSelect.options, function (o) {
      if ((o.getAttribute('data-topic') || '') === wantTopic) o.selected = true;
    });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = form.elements.name.value.trim();
    if (!name) { say('A name helps.'); form.elements.name.focus(); return; }
    var email = form.elements.email.value.trim();
    if (!email || email.indexOf('@') < 1) {
      say('We need an email address to reply to.'); form.elements.email.focus(); return;
    }

    var body = [
      'Name: ' + name,
      'Email: ' + email,
      'Organisation: ' + (form.elements.org.value.trim() || '—'),
      'Request: ' + form.elements.topic.value,
      'Estate: ' + (form.elements.estate.value.trim() || '—'),
      '', form.elements.message.value.trim()
    ].join('\n');

    if (endpoint) {
      submit.disabled = true; say('Sending…');
      fetch(endpoint, { method: 'POST', headers: { 'Accept': 'application/json' },
                        body: new FormData(form) })
        .then(function (r) { if (!r.ok) throw new Error(r.status);
          form.hidden = true; thanks.hidden = false;
          thanks.setAttribute('tabindex', '-1'); thanks.focus(); })
        .catch(function () { submit.disabled = false;
          say('That did not send. Try again, or email us — your message is still in the form.'); });
      return;
    }

    if (!contact) {
      say('Could not open your mail client. Copy the message below and send it to us.');
      document.getElementById('cf-copy').value = body;
      fallback.hidden = false;
      return;
    }
    window.location.href = 'mailto:' + contact
      + '?subject=' + encodeURIComponent('SeQontrol — ' + form.elements.topic.value)
      + '&body=' + encodeURIComponent(body);
    say('Opening your mail client…');
    document.getElementById('cf-copy').value =
      'To: ' + contact + '\nSubject: SeQontrol — ' + form.elements.topic.value + '\n\n' + body;
    window.setTimeout(function () { fallback.hidden = false; }, 1200);
  });

  var copyBtn = document.getElementById('cf-copy-btn');
  if (copyBtn) copyBtn.addEventListener('click', function () {
    var box = document.getElementById('cf-copy');
    box.select();
    var done = function () { copyBtn.textContent = 'Copied'; };
    if (navigator.clipboard) navigator.clipboard.writeText(box.value).then(done, function () {});
    else { document.execCommand('copy'); done(); }
  });
})();
