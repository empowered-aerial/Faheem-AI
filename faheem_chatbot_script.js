const API_BASE = "http://127.0.0.1:8000";
const SESSION_KEY = "faheem_session_id";

const messagesEl = document.getElementById("messages");
const input = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const reportContent = document.getElementById("reportContent");
const statusEl = document.getElementById("connectionStatus");
const micBtn = document.getElementById("micBtn");
const voiceStatus = document.getElementById("voiceStatus");
const newReportBtn = document.getElementById("newReportBtn");

let recorder = null;
let recordingStream = null;
let recordingChunks = [];
let isRecording = false;
let isSending = false;
let sessionId = localStorage.getItem(SESSION_KEY) || null;

window.getFaheemSessionId = () => sessionId;
window.faheemActiveSessionId = sessionId;

function updateSessionId(value) {
    sessionId = value || null;

    if (sessionId) {
        localStorage.setItem(SESSION_KEY, sessionId);
    } else {
        localStorage.removeItem(SESSION_KEY);
    }

    window.faheemActiveSessionId = sessionId;
}

function addMessage(text, type) {
    const message = document.createElement("div");
    message.className = `message ${type}`;
    message.textContent = text;

    messagesEl.appendChild(message);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    return message;
}

function setStatus(online, text) {
    statusEl.textContent = text;
    statusEl.dataset.state = online ? "online" : "offline";
}

function renderReport(data) {
    if (typeof window.faheemRenderReportReview === "function") {
        window.faheemRenderReportReview(data);
        return;
    }

    if (!data || !data.report || !data.report_ready) {
        reportContent.textContent =
            "سيظهر ملخص البلاغ هنا بعد اكتمال المعلومات المطلوبة.";
        return;
    }

    reportContent.textContent =
        data.report_ar || "تم إنشاء مسودة البلاغ.";

    reportContent.dir = "rtl";
    reportContent.style.whiteSpace = "pre-wrap";
}

function setSending(value) {
    isSending = value;

    sendBtn.disabled = value;
    input.disabled = value;
    micBtn.disabled = value || isRecording;
    newReportBtn.disabled = value || isRecording;

    sendBtn.textContent = value ? "جارٍ الإرسال..." : "إرسال";
}

async function saveReportDraft(data) {
    const sid = data.session_id || sessionId;
    const report = data.report;

    if (!sid || !report || !report.report_id) {
        throw new Error("بيانات مسودة البلاغ غير مكتملة.");
    }

    const response = await fetch(
        `${API_BASE}/api/reports/${encodeURIComponent(sid)}`,
        {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                report
            })
        }
    );

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(
            typeof result.detail === "string"
                ? result.detail
                : `تعذر حفظ البلاغ (${response.status}).`
        );
    }

    if (!result.report) {
        throw new Error("لم يُرجع الخادم نسخة محفوظة من البلاغ.");
    }

    return result.report;
}

async function sendMessage(textOverride) {
    const text = (textOverride ?? input.value).trim();

    if (!text || isSending || isRecording) return;

    addMessage(text, "user");

    input.value = "";
    input.style.height = "auto";

    setSending(true);

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: text
            })
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            if (response.status === 410) {
                updateSessionId(null);
                renderReport(null);
            }

            throw new Error(
                typeof data.detail === "string"
                    ? data.detail
                    : `تعذر إكمال الطلب (${response.status}).`
            );
        }

        updateSessionId(data.session_id || sessionId);

        addMessage(
            data.reply_ar || "تمت معالجة رسالتك.",
            "bot"
        );

        if (data.report_ready && data.report) {
            try {
                const savedReport = await saveReportDraft(data);

                data.report = savedReport;
                data.report_ready = true;

                renderReport(data);

                console.log(
                    "FAHEEM report saved:",
                    savedReport.report_id
                );
            } catch (error) {
                renderReport(null);

                addMessage(
                    `تعذر حفظ مسودة البلاغ: ${error.message}`,
                    "error"
                );

                console.error("Report saving failed:", error);
            }
        } else {
            renderReport(null);
        }

        setStatus(true, "متصل بمحرك فهيم");

    } catch (error) {
        addMessage(
            `تعذر الاتصال بمحرك فهيم: ${error.message}`,
            "error"
        );

        setStatus(false, "تعذر الاتصال بالخادم");
        console.error(error);

    } finally {
        setSending(false);
        input.focus();
    }
}

function setVoiceStatus(text, isError = false) {
    voiceStatus.textContent = text;
    voiceStatus.style.color = isError
        ? "var(--danger)"
        : "var(--muted)";
}

function stopRecordingStream() {
    if (recordingStream) {
        recordingStream.getTracks().forEach(track => track.stop());
        recordingStream = null;
    }
}

function resetRecordingUI() {
    isRecording = false;
    recorder = null;

    stopRecordingStream();

    micBtn.textContent = "🎙️";
    micBtn.classList.remove("recording");

    input.disabled = isSending;
    sendBtn.disabled = isSending;
    micBtn.disabled = isSending;
    newReportBtn.disabled = isSending;
}

async function startVoiceRecording() {
    if (isSending || isRecording) return;

    if (
        !navigator.mediaDevices?.getUserMedia ||
        !window.MediaRecorder
    ) {
        setVoiceStatus(
            "المتصفح لا يدعم التسجيل الصوتي.",
            true
        );
        return;
    }

    try {
        recordingStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        const formats = [
            "audio/webm;codecs=opus",
            "audio/webm",
            "audio/ogg;codecs=opus",
            "audio/mp4"
        ];

        const selectedFormat = formats.find(format =>
            MediaRecorder.isTypeSupported(format)
        );

        recorder = selectedFormat
            ? new MediaRecorder(recordingStream, {
                mimeType: selectedFormat
            })
            : new MediaRecorder(recordingStream);

        recordingChunks = [];

        recorder.ondataavailable = event => {
            if (event.data.size > 0) {
                recordingChunks.push(event.data);
            }
        };

        recorder.onerror = () => {
            resetRecordingUI();

            setVoiceStatus(
                "حدث خطأ أثناء التسجيل الصوتي.",
                true
            );
        };

        recorder.onstop = () => {
            const mimeType = recorder?.mimeType || "audio/webm";

            const blob = new Blob(recordingChunks, {
                type: mimeType
            });

            resetRecordingUI();

            if (!blob.size) {
                setVoiceStatus(
                    "لم يتم تسجيل أي صوت.",
                    true
                );
                return;
            }

            transcribeRecording(blob);
        };

        recorder.start();

        isRecording = true;

        micBtn.textContent = "⏹";
        micBtn.classList.add("recording");

        input.disabled = true;
        sendBtn.disabled = true;
        newReportBtn.disabled = true;

        setVoiceStatus(
            "جارٍ التسجيل... اضغط لإيقاف التسجيل."
        );

    } catch (error) {
        resetRecordingUI();

        setVoiceStatus(
            "تعذر الوصول إلى الميكروفون. تحقق من صلاحيات المتصفح.",
            true
        );

        console.error(error);
    }
}

function stopVoiceRecording() {
    if (!recorder || recorder.state === "inactive") return;

    micBtn.disabled = true;

    setVoiceStatus(
        "تم إيقاف التسجيل. جارٍ تجهيز الصوت..."
    );

    recorder.stop();
}

async function transcribeRecording(blob) {
    setSending(true);

    setVoiceStatus(
        "جارٍ تحويل الصوت إلى نص باستخدام Whisper..."
    );

    const formData = new FormData();
    const mime = (blob.type || "audio/webm").split(";")[0];

    const extension = mime.includes("ogg")
        ? "ogg"
        : mime.includes("mp4")
        ? "mp4"
        : mime.includes("mpeg")
        ? "mp3"
        : mime.includes("wav")
        ? "wav"
        : "webm";

    formData.append(
        "audio",
        blob,
        `faheem-recording.${extension}`
    );

    try {
        const response = await fetch(
            `${API_BASE}/api/transcribe`,
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(
                data.detail ||
                `Transcription failed (${response.status})`
            );
        }

        const transcript = (data.transcript || "").trim();

        if (!transcript) {
            throw new Error("لم يتم التعرف على الكلام.");
        }

        input.value = transcript;
        input.style.height = "auto";
        input.style.height =
            `${Math.min(input.scrollHeight, 120)}px`;

        setVoiceStatus(
            "تم تحويل الصوت بنجاح. راجع النص وعدّله ثم اضغط إرسال."
        );

    } catch (error) {
        setVoiceStatus(
            `تعذر تحويل التسجيل: ${error.message}`,
            true
        );

        console.error(error);

    } finally {
        setSending(false);
        input.focus();
    }
}

async function newReport() {
    if (isSending || isRecording) return;

    const oldSessionId = sessionId;

    updateSessionId(null);

    messagesEl.replaceChildren();

    addMessage(
        "مرحباً بك في فهيم. صف المشكلة التي ترغب في الإبلاغ عنها، وسأساعدك في إعداد البلاغ.",
        "bot"
    );

    renderReport(null);
    setVoiceStatus("");
    setStatus(true, "جاهز للاتصال");

    if (oldSessionId) {
        const encodedId = encodeURIComponent(oldSessionId);

        await Promise.allSettled([
            fetch(`${API_BASE}/api/chat/${encodedId}`, {
                method: "DELETE"
            }),
            fetch(`${API_BASE}/api/reports/${encodedId}`, {
                method: "DELETE"
            })
        ]);
    }

    input.value = "";
    input.style.height = "auto";
}

function quickSend(text) {
    sendMessage(text);
}

window.newReport = newReport;
window.quickSend = quickSend;
window.sendFaheemMessage = sendMessage;

micBtn.addEventListener("click", () => {
    if (isRecording) {
        stopVoiceRecording();
    } else {
        startVoiceRecording();
    }
});

sendBtn.addEventListener("click", () => sendMessage());

input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height =
        `${Math.min(input.scrollHeight, 120)}px`;
});

newReportBtn.addEventListener("click", newReport);

document.querySelectorAll("[data-quick-message]").forEach(button => {
    button.addEventListener("click", () => {
        quickSend(button.dataset.quickMessage);
    });
});

newReport();