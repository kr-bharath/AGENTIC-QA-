describe('DOM Crawler', () => {
    it('Crawls the target page and extracts interactive elements', () => {
      // Ignore website JS errors to prevent Cypress from forcefully crashing the extraction
      cy.on('uncaught:exception', (err, runnable) => {
        return false;
      });

      // Visit the FULL baseUrl (Cypress resolves '/' relative to baseUrl root, 
      // so we use the config baseUrl directly to preserve subpaths like /products, /login etc.)
      const targetUrl = Cypress.config('baseUrl');
      cy.visit(targetUrl, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Windows"'
        },
        failOnStatusCode: false
      });

      // Wait for Single Page Applications to fully hydrate their DOM
      cy.wait(5000);

      // =====================================================================
      // PHASE 1: Auto-Dismiss Cookie Consent / GDPR Banners
      // Uses multi-strategy approach to handle different consent frameworks
      // =====================================================================
      
      // Strategy 1: Click common "Accept" / "Agree" / "Consent" buttons by text content
      cy.document().then((doc) => {
        // Common button texts used by GDPR/cookie consent banners worldwide
        const acceptTexts = [
          'accept all', 'accept cookies', 'accept', 'agree', 'agree & proceed',
          'allow all', 'allow cookies', 'allow all cookies', 'i agree', 'i accept',
          'got it', 'ok', 'okay', 'continue', 'close', 'dismiss',
          'yes, i agree', 'consent', 'acknowledge', 'understood',
          'accept and continue', 'accept & close', 'that\'s ok',
          'alle akzeptieren', 'akzeptieren', 'tout accepter', 'accepter',
          'aceptar todo', 'aceptar', 'accetta tutti', 'accetta'
        ];
        
        // Search for clickable elements (buttons, links, divs with role=button)
        const clickables = doc.querySelectorAll(
          'button, a, [role="button"], input[type="button"], input[type="submit"], ' +
          '[class*="consent"] [class*="accept"], [class*="cookie"] button, ' +
          '[id*="consent"] button, [id*="cookie"] button, ' +
          '[class*="gdpr"] button, [id*="gdpr"] button, ' +
          '[data-testid*="accept"], [data-testid*="consent"], [data-testid*="cookie"]'
        );
        
        let consentClicked = false;
        clickables.forEach((el) => {
          if (consentClicked) return;
          const elText = (el.innerText || el.value || el.getAttribute('aria-label') || '').toLowerCase().trim();
          for (const acceptText of acceptTexts) {
            if (elText === acceptText || elText.includes(acceptText)) {
              try {
                el.click();
                consentClicked = true;
                cy.log(`Cookie consent auto-dismissed by clicking: "${elText}"`);
              } catch (e) {
                // Click failed, try next
              }
              break;
            }
          }
        });
        
        // Strategy 2: Handle OneTrust (used by StackOverflow, many enterprise sites)
        const oneTrustAccept = doc.querySelector('#onetrust-accept-btn-handler');
        if (oneTrustAccept && !consentClicked) {
          try { oneTrustAccept.click(); consentClicked = true; cy.log('OneTrust consent dismissed.'); } catch(e) {}
        }
        
        // Strategy 3: Handle CookieBot (used by many EU sites)
        const cookiebotAccept = doc.querySelector('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll, #CybotCookiebotDialogBodyButtonAccept');
        if (cookiebotAccept && !consentClicked) {
          try { cookiebotAccept.click(); consentClicked = true; cy.log('CookieBot consent dismissed.'); } catch(e) {}
        }
        
        // Strategy 4: Handle Quantcast/TCFv2 frameworks
        const quantcastAccept = doc.querySelector('.qc-cmp2-summary-buttons button[mode="primary"], .qc-cmp-button');
        if (quantcastAccept && !consentClicked) {
          try { quantcastAccept.click(); consentClicked = true; cy.log('Quantcast consent dismissed.'); } catch(e) {}
        }
        
        // Strategy 5: Handle TrustArc / Evidon
        const trustarcAccept = doc.querySelector('.pdynamicbutton .call, #truste-consent-button, .evidon-consent-button');
        if (trustarcAccept && !consentClicked) {
          try { trustarcAccept.click(); consentClicked = true; cy.log('TrustArc consent dismissed.'); } catch(e) {}
        }
      });

      cy.wait(1500);

      // =====================================================================
      // PHASE 2: Remove Blocking Overlays, Modals, and Consent Iframes from DOM
      // =====================================================================
      cy.document().then((doc) => {
        // Remove consent iframes (Google consent, CMP providers, etc.)
        const consentIframeSelectors = [
          'iframe[src*="consent"]', 'iframe[src*="cookie"]', 'iframe[src*="gdpr"]',
          'iframe[src*="onetrust"]', 'iframe[src*="cookiebot"]', 'iframe[src*="quantcast"]',
          'iframe[src*="trustarc"]', 'iframe[src*="consentmanager"]',
          'iframe[src*="privacy"]', 'iframe[id*="consent"]'
        ];
        consentIframeSelectors.forEach(sel => {
          doc.querySelectorAll(sel).forEach(el => {
            try { el.remove(); } catch(e) {}
          });
        });
        
        // Remove overlay/blocking elements by common identifiers
        const overlaySelectors = [
          '[id*="dismiss"]', '[class*="consent"]', '[class*="cookie-banner"]',
          '[class*="cookie-notice"]', '[class*="cookie-popup"]', '[class*="cookie-wall"]',
          '[class*="overlay"]', '[id*="ad_position"]', '[class*="gdpr"]',
          '[id*="onetrust"]', '[id*="cookie"]', '[class*="cc-banner"]',
          '[class*="cc-window"]', '[class*="js-consent"]', '[id*="consent"]',
          '[class*="privacy-banner"]', '[class*="cookie-modal"]',
          '[data-nosnippet]', '[class*="sp_veil"]', '[id*="sp_message"]',
          '.fc-consent-root', '.cmpbox', '#cmp-container',
          '[class*="notice-banner"]', '[class*="alert-banner"]'
        ];
        overlaySelectors.forEach(sel => {
          doc.querySelectorAll(sel).forEach(el => {
            // Check if it looks like a consent overlay (fixed/sticky position, covers viewport)
            const style = window.getComputedStyle(el);
            const isOverlay = style.position === 'fixed' || style.position === 'sticky' 
                            || style.position === 'absolute' || el.getAttribute('role') === 'dialog'
                            || el.getAttribute('role') === 'alertdialog';
            if (isOverlay) {
              try { el.remove(); } catch(e) {}
            }
          });
        });
        
        // Fix body scroll if consent banner locked it (many sites add overflow:hidden to body)
        doc.body.style.overflow = 'auto';
        doc.documentElement.style.overflow = 'auto';
        
        // Remove any backdrop/dimmer overlays
        doc.querySelectorAll('[class*="backdrop"], [class*="dimmer"], [class*="shade"]').forEach(el => {
          const style = window.getComputedStyle(el);
          if (style.position === 'fixed' || style.position === 'absolute') {
            try { el.remove(); } catch(e) {}
          }
        });
      });

      cy.wait(1000);

      // =====================================================================
      // PHASE 3: Detect Cloudflare / Bot Protection Walls
      // If detected, flag it in the output so the pipeline can log a clear reason
      // =====================================================================
      let isBotBlocked = false;
      cy.document().then((doc) => {
        const bodyText = (doc.body.innerText || '').toLowerCase();
        const botIndicators = [
          'checking your browser', 'just a moment', 'cloudflare', 
          'ray id', 'please verify you are a human',
          'access denied', 'attention required', 'enable javascript and cookies',
          'captcha', 'are you a robot', 'bot protection',
          'please complete the security check', 'ddos protection'
        ];
        
        for (const indicator of botIndicators) {
          if (bodyText.includes(indicator)) {
            isBotBlocked = true;
            cy.log(`⚠️ BOT PROTECTION DETECTED: Page contains "${indicator}". DOM extraction may be limited.`);
            break;
          }
        }
      });

      // =====================================================================
      // PHASE 4: Scroll & Lazy-Load Trigger
      // =====================================================================
      cy.scrollTo('bottom', { ensureScrollable: false });
      cy.wait(2000);
  
      // =====================================================================
      // PHASE 5: Extract Interactive DOM Elements
      // =====================================================================
      cy.document().then((doc) => {
        const elements = [];
        const interactiveSelectors = 'input, button, a[href], select, textarea, form';
  
        const interactives = doc.querySelectorAll(interactiveSelectors);
  
        interactives.forEach((el, index) => {
          const tag = el.tagName.toLowerCase();
          const id = el.id ? `#${el.id}` : '';
          const classList = Array.from(el.classList).join('.');
          const classes = classList ? `.${classList}` : '';
          const type = el.getAttribute('type') || '';
          const name = el.getAttribute('name') || '';
          const href = el.getAttribute('href') || '';
          const text = el.innerText ? el.innerText.substring(0, 50).trim() : '';
  
          elements.push({
            id: index,
            tag: tag,
            selector_guess: `${tag}${id}${classes}`,
            type: type,
            name: name,
            href: href,
            text: text,
            isVisible: el.offsetWidth > 0 && el.offsetHeight > 0
          });
        });
  
        const domData = {
          url: doc.location.href,
          timestamp: new Date().toISOString(),
          total_extracted: elements.length,
          bot_protection_detected: isBotBlocked,
          elements: elements
        };
  
        const runId = Cypress.env("run_id") || "dom_structure";
        cy.task('saveDomData', {
          filename: `${runId}.json`,
          data: domData
        });
        
        if (isBotBlocked) {
          cy.log(`⚠️ Bot protection was detected. Only ${elements.length} elements extracted (may be from challenge page).`);
        } else {
          cy.log(`✅ Extracted ${elements.length} interactive elements and saved to JSON.`);
        }
      });
    });
  });
