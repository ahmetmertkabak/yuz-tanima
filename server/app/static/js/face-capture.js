/**
 * Face enrollment — webcam capture workflow.
 *
 * Usage:
 *   FaceCapture.init({
 *     personId: 42,
 *     endpoint: "/persons/42/face",
 *     csrfToken: "...",
 *     minFrames: 3,
 *     targetFrames: 5,
 *     quality: 0.85
 *   });
 */
(function (global) {
  const FaceCapture = {
    config: {
      minFrames: 3,
      targetFrames: 5,
      quality: 0.85
    },
    state: {
      stream: null,
      frames: [],
      video: null,
      canvas: null
    },

    init(options) {
      Object.assign(this.config, options);

      this.state.video = document.getElementById("face-video");
      this.state.canvas = document.getElementById("face-canvas");
      const thumbs = document.getElementById("thumbnails");
      const overlay = document.getElementById("face-overlay");
      const captureBtn = document.getElementById("capture-btn");
      const resetBtn = document.getElementById("reset-btn");
      const submitBtn = document.getElementById("submit-frames-btn");
      const statusAlert = document.getElementById("status-alert");
      const modal = document.getElementById("faceModal");

      const showStatus = (msg, type = "info") => {
        statusAlert.className = `alert alert-${type} small mt-3`;
        statusAlert.textContent = msg;
        statusAlert.classList.remove("d-none");
      };
      const hideStatus = () => statusAlert.classList.add("d-none");

      const updateButton = () => {
        captureBtn.innerHTML =
          `<i class="bi bi-camera-fill"></i> Fotoğraf Çek (${this.state.frames.length}/${this.config.targetFrames})`;
        captureBtn.disabled = this.state.frames.length >= this.config.targetFrames;
        submitBtn.disabled = this.state.frames.length < this.config.minFrames;
      };

      const startStream = async () => {
        try {
          this.state.stream = await navigator.mediaDevices.getUserMedia({
            video: {
              facingMode: "user",
              width: { ideal: 640 },
              height: { ideal: 480 }
            },
            audio: false
          });
          this.state.video.srcObject = this.state.stream;
          overlay.style.display = "none";
          captureBtn.disabled = false;
        } catch (err) {
          showStatus(`Kameraya erişilemedi: ${err.message}`, "danger");
        }
      };

      const stopStream = () => {
        if (this.state.stream) {
          this.state.stream.getTracks().forEach(t => t.stop());
          this.state.stream = null;
        }
      };

      const resetFrames = () => {
        this.state.frames = [];
        thumbs.innerHTML = "";
        updateButton();
        hideStatus();
      };

      const captureFrame = () => {
        const video = this.state.video;
        const canvas = this.state.canvas;
        const w = video.videoWidth;
        const h = video.videoHeight;
        if (!w || !h) return;

        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, w, h);

        const dataUrl = canvas.toDataURL("image/jpeg", this.config.quality);
        this.state.frames.push(dataUrl);

        const thumb = document.createElement("div");
        thumb.className = "position-relative";
        thumb.style.width = "72px";
        thumb.innerHTML = `
          <img src="${dataUrl}" class="rounded border" style="width:72px;height:54px;object-fit:cover">
          <button type="button" class="btn-close position-absolute top-0 end-0 bg-white"
                  style="font-size:0.65rem" aria-label="Sil"></button>
        `;
        thumb.querySelector("button").addEventListener("click", () => {
          const i = Array.from(thumbs.children).indexOf(thumb);
          if (i >= 0) {
            this.state.frames.splice(i, 1);
            thumb.remove();
            updateButton();
          }
        });
        thumbs.appendChild(thumb);
        updateButton();
      };

      const submit = async () => {
        if (this.state.frames.length < this.config.minFrames) return;
        submitBtn.disabled = true;
        showStatus("Yüz encoding hesaplanıyor, lütfen bekleyin...", "info");

        try {
          const res = await fetch(this.config.endpoint, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this.config.csrfToken
            },
            body: JSON.stringify({ frames: this.state.frames })
          });
          const body = await res.json();
          if (!res.ok) {
            const msg = body.message || body.error || `Hata (${res.status})`;
            showStatus(msg, "danger");
            submitBtn.disabled = false;
            return;
          }
          showStatus(
            `Kaydedildi! ${body.frames_used} kare kullanıldı. Cihazlara 1-2 dakika içinde yayılır.`,
            "success"
          );
          setTimeout(() => location.reload(), 1200);
        } catch (err) {
          showStatus(`Sunucu hatası: ${err.message}`, "danger");
          submitBtn.disabled = false;
        }
      };

      captureBtn.addEventListener("click", captureFrame);
      resetBtn.addEventListener("click", resetFrames);
      submitBtn.addEventListener("click", submit);

      modal.addEventListener("shown.bs.modal", startStream);
      modal.addEventListener("hidden.bs.modal", () => {
        stopStream();
        resetFrames();
      });

      updateButton();
    }
  };

  global.FaceCapture = FaceCapture;
})(window);