/* One shared recording; timestamps use the original mixed-recording clock.
   Device files are verified and played locally. No upload or persistent copy. */
(function (root) {
  'use strict';
  function createPlayer(options) {
    const audio = options.audio;
    const status = options.status || function () {};
    const active = options.active || function () {};
    let serial = 0, selected = null, sourceReady = false, wantsPlay = false, pendingPlay = false;
    let cancelMetadata = null, internalPause = false;
    function pauseMedia() {
      internalPause = true;
      audio.pause();
      internalPause = false;
    }
    function cancelPending() {
      serial += 1;
      if (cancelMetadata) cancelMetadata();
      cancelMetadata = null;
    }
    function clear() { active(null); selected = null; }
    function metadata() {
      if (audio.readyState >= 1) return Promise.resolve();
      return new Promise(function (resolve, reject) {
        let timer;
        function cleanup() {
          clearTimeout(timer);
          audio.removeEventListener('loadedmetadata', done);
          audio.removeEventListener('error', fail);
          if (cancelMetadata === cancel) cancelMetadata = null;
        }
        function done() { cleanup(); resolve(); }
        function fail() { cleanup(); reject(new Error('metadata')); }
        function cancel() { cleanup(); reject(Object.assign(new Error('cancelled'), {name: 'AbortError'})); }
        cancelMetadata = cancel;
        audio.addEventListener('loadedmetadata', done);
        audio.addEventListener('error', fail);
        timer = setTimeout(fail, 20000);
      });
    }
    async function playFrom(button, start) {
      if (!Number.isFinite(start) || start < 0) {
        status('This line has no usable timestamp.'); return;
      }
      if (!sourceReady) { options.needFile(); return; }
      if (selected === button && wantsPlay && (!audio.paused || pendingPlay)) {
        cancelPending(); wantsPlay = false; pendingPlay = false; pauseMedia(); clear(); status('Paused.'); return;
      }
      cancelPending();
      const request = serial;
      wantsPlay = false; pauseMedia(); clear();
      selected = button; wantsPlay = true; pendingPlay = true;
      status('Loading this moment…');
      try {
        await metadata();
        if (request !== serial) return;
        if (!Number.isFinite(audio.duration) || audio.duration <= 0 || start >= audio.duration) {
          throw new Error('timestamp');
        }
        audio.currentTime = Math.max(0, start - 0.35);
        await audio.play();
        if (request !== serial) {
          if (!wantsPlay) pauseMedia();
          return;
        }
        pendingPlay = false;
        active(button);
        status('Playing — tap the same button to pause.');
      } catch (error) {
        if (request !== serial) return;
        wantsPlay = false; pendingPlay = false; clear();
        if (error.name === 'NotAllowedError') status('Recording ready. Tap a line’s play button again.');
        else if (error.message === 'timestamp') status('That timestamp is outside this recording. Check the selected file.');
        else if (error.name === 'AbortError') status('Paused. Tap a line to retry.');
        else status('Could not play this moment. Tap to retry or choose the recording again.');
      }
    }
    function setSource(url) {
      cancelPending(); wantsPlay = false; pendingPlay = false; pauseMedia(); clear();
      sourceReady = Boolean(url);
      if (url) audio.src = url;
      else audio.removeAttribute('src');
      audio.load();
    }
    function onPause() {
      // A delayed pause event from seeking must not cancel a new play request.
      if (internalPause || pendingPlay || !audio.paused) return;
      cancelPending(); wantsPlay = false; clear(); status('Paused.');
    }
    function onEnd() { cancelPending(); wantsPlay = false; pendingPlay = false; clear(); status('Recording ended. Tap any line to replay.'); }
    function onError() { cancelPending(); wantsPlay = false; pendingPlay = false; clear(); status('Audio could not load. Choose the correct recording and try again.'); }
    audio.addEventListener('pause', onPause);
    audio.addEventListener('ended', onEnd);
    audio.addEventListener('error', onError);
    return {playFrom, setSource, destroy: function () {
      cancelPending(); wantsPlay = false; pendingPlay = false; pauseMedia(); clear();
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('ended', onEnd);
      audio.removeEventListener('error', onError);
    }};
  }

  async function verifyFile(file, expected, digest) {
    if (file.size !== expected.bytes) throw new Error('wrong-file');
    const bytes = await file.arrayBuffer();
    const result = await digest('SHA-256', bytes);
    const hash = Array.from(new Uint8Array(result), n => n.toString(16).padStart(2, '0')).join('');
    if (hash !== expected.sha256) throw new Error('wrong-file');
    return true;
  }

  function mount(doc, win) {
    const panel = doc.getElementById('lesson-audio-panel');
    if (!panel) return null;
    const audio = doc.getElementById('lesson-audio');
    const input = doc.getElementById('lesson-audio-file');
    const choose = doc.getElementById('lesson-audio-choose');
    const status = doc.getElementById('lesson-audio-status');
    const buttons = Array.from(doc.querySelectorAll('.line-play'));
    let objectUrl = null, fileSerial = 0;
    const player = createPlayer({audio, status: text => { status.textContent = text; },
      needFile: function () { status.textContent = 'Choose this lesson’s full recording once, then tap any line.'; input.click(); },
      active: function (selected) {
        buttons.forEach(button => {
          const on = button === selected;
          button.classList.toggle('playing', on);
          button.setAttribute('aria-pressed', String(on));
          button.textContent = on ? '❚❚' : '▶';
          button.setAttribute('aria-label', (on ? 'Pause ' : 'Play ') + button.dataset.label);
        });
      }});
    buttons.forEach(button => {
      button.disabled = false;
      button.addEventListener('click', () => player.playFrom(button, Number(button.dataset.start)));
    });
    choose.addEventListener('click', () => input.click());
    input.addEventListener('change', async function () {
      const file = input.files && input.files[0];
      input.value = '';
      if (!file) return; // Cancelling the picker keeps the existing recording.
      const request = ++fileSerial;
      status.textContent = 'Checking the recording on your device…';
      choose.disabled = true;
      try {
        if (!win.crypto || !win.crypto.subtle) throw new Error('verification-unavailable');
        await verifyFile(file, {bytes: Number(panel.dataset.bytes), sha256: panel.dataset.sha256},
          win.crypto.subtle.digest.bind(win.crypto.subtle));
        if (request !== fileSerial) return;
        const next = win.URL.createObjectURL(file);
        const previous = objectUrl;
        objectUrl = next;
        player.setSource(next);
        if (previous) win.URL.revokeObjectURL(previous);
        audio.hidden = false;
        choose.textContent = 'Change recording';
        status.textContent = 'Correct recording selected. Tap any ▶. Nothing was uploaded.';
      } catch (error) {
        if (request !== fileSerial) return;
        status.textContent = error.message === 'wrong-file'
          ? 'That is not the matching full lesson recording. Choose the September 5 mixed audio.mp3.'
          : 'Could not verify this file. Open the HTTPS hub in a current browser and try again.';
      } finally { if (request === fileSerial) choose.disabled = false; }
    });
    function cleanup() {
      fileSerial += 1; player.destroy();
      if (objectUrl) win.URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }
    win.addEventListener('pagehide', event => { if (!event.persisted) cleanup(); });
    return {player, cleanup};
  }
  if (typeof module === 'object' && module.exports) module.exports = {createPlayer, verifyFile, mount};
  else root.AneesTranscriptPlayer = {createPlayer, verifyFile, mount};
  if (typeof document !== 'undefined') mount(document, root);
})(typeof window === 'undefined' ? globalThis : window);
