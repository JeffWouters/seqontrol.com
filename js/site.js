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
