const { defineConfig } = require("cypress");
const fs = require('fs');

module.exports = defineConfig({
  e2e: {
    baseUrl: 'https://www.facebook.com/',
    setupNodeEvents(on, config) {
      // Modify Chrome launch args to bypass basic bot detection
      on('before:browser:launch', (browser, launchOptions) => {
        if (browser.family === 'chromium' && browser.name !== 'electron') {
          // Remove automation flags that bot detectors look for
          launchOptions.args = launchOptions.args.filter(
            arg => !arg.includes('--enable-automation')
          );
          launchOptions.args.push('--disable-blink-features=AutomationControlled');
          launchOptions.args.push('--disable-features=IsolateOrigins,site-per-process');
          launchOptions.args.push('--disable-site-isolation-trials');
          launchOptions.args.push('--disable-web-security');
          launchOptions.args.push('--allow-running-insecure-content');
        }
        return launchOptions;
      });

      on('before:spec', (spec) => {
        // Automatically clear any cached state or downloads from previous tests
        console.log(`Starting execution for: ${spec.name}`);
      });
      on('after:spec', (spec, results) => {
        if (results) {
          try {
            const outPath = `./results/${spec.name}_status.json`;
            
            // Extract real error messages from Cypress test results for Root Cause Analysis
            let errorMessage = null;
            let errorStack = null;
            let errorType = null;
            
            if (results.stats.failures > 0 && results.tests && results.tests.length > 0) {
              for (const test of results.tests) {
                if (test.attempts && test.attempts.length > 0) {
                  const lastAttempt = test.attempts[test.attempts.length - 1];
                  if (lastAttempt.error) {
                    errorMessage = lastAttempt.error.message || null;
                    errorStack = lastAttempt.error.stack || null;
                    
                    // Classify the error type for smarter Root Cause Analysis
                    const msg = (errorMessage || '').toLowerCase();
                    if (msg.includes('timeout') || msg.includes('timed out')) {
                      errorType = 'TIMEOUT';
                    } else if (msg.includes('not found') || msg.includes('could not find') || msg.includes('does not exist')) {
                      errorType = 'ELEMENT_NOT_FOUND';
                    } else if (msg.includes('detached') || msg.includes('stale')) {
                      errorType = 'DETACHED_DOM';
                    } else if (msg.includes('assert') || msg.includes('expected')) {
                      errorType = 'ASSERTION_FAILURE';
                    } else if (msg.includes('syntax') || msg.includes('unexpected token')) {
                      errorType = 'SYNTAX_ERROR';
                    } else if (msg.includes('navigation') || msg.includes('url')) {
                      errorType = 'NAVIGATION_FAILURE';
                    } else {
                      errorType = 'UNKNOWN';
                    }
                    break;
                  }
                }
              }
            }

            const payload = {
                failed: results.stats.failures > 0,
                duration: results.stats.duration || 0,
                spec: spec.name,
                errorMessage: errorMessage,
                errorStack: errorStack,
                errorType: errorType
            };
            fs.writeFileSync(outPath, JSON.stringify(payload, null, 2));
          } catch (e) {
            console.error("Failed to write spec status payload:", e);
          }
        }
      });
      on('task', {
        // Save DOM structure JSON to disk
        saveDomData({ filename, data }) {
          const path = `./data/${filename}`;
          fs.writeFileSync(path, JSON.stringify(data, null, 2));
          return null; // Signals task completed
        }
      });
    },
    defaultCommandTimeout: 10000,
    pageLoadTimeout: 20000,
    supportFile: false,
    chromeWebSecurity: false,
  },
  video: false,
  screenshotOnRunFailure: true
});
