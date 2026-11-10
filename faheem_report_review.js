(() => {
    const API = "http://127.0.0.1:8000";
    const SESSION_KEY = "faheem_session_id";

    const CATEGORY_LABELS = {
        road_infrastructure: "البنية التحتية والطرق",
        street_lighting: "إنارة الشوارع",
        waste_management: "إدارة النفايات",
        public_facilities: "المرافق العامة",
        water_supply: "إمدادات المياه",
        drainage: "تصريف مياه الأمطار",
        traffic: "السلامة المرورية",
        other: "بلاغ عام"
    };

    const SUBCATEGORIES = {
        road_infrastructure: {
            pothole: "حفرة في الطريق",
            damaged_road: "طريق متضرر",
            road_damage: "تلف الطريق",
            damaged_road_surface: "تلف سطح الطريق",
            damaged_sidewalk: "تلف الرصيف",
            damaged_manhole: "غطاء منهول تالف",
            road_obstruction: "عائق في الطريق"
        },
        street_lighting: {
            light_not_working: "إنارة لا تعمل",
            streetlight_failure: "تعطل إنارة الشارع",
            broken_streetlight: "عمود إنارة معطل",
            flickering_light: "إنارة متقطعة",
            damaged_pole: "عمود إنارة تالف",
            exposed_wiring: "أسلاك مكشوفة"
        },
        waste_management: {
            missed_collection: "تأخر جمع النفايات",
            overflowing_bin: "حاوية ممتلئة",
            illegal_dumping: "رمي نفايات عشوائي",
            accumulated_litter: "تراكم النفايات",
            waste_accumulation: "تراكم النفايات"
        },
        public_facilities: {
            damaged_bench: "مقعد تالف",
            playground_damage: "تلف ألعاب الأطفال",
            park_facility_damage: "تلف مرفق عام",
            public_toilet_issue: "مشكلة في دورة المياه العامة"
        },
        water_supply: {
            water_leak: "تسرب مياه"
        },
        drainage: {
            blocked_drain: "انسداد تصريف المياه"
        },
        traffic: {
            road_obstruction: "عائق في الطريق"
        }
    };

    const styles = document.createElement("style");

    styles.textContent = `
        .fr-tools {
            margin-top: 14px;
            padding: 15px;
            border: 1px solid rgba(255,255,255,.13);
            border-radius: 16px;
            background: rgba(255,255,255,.035);
            direction: rtl;
            color: inherit;
            font-family: inherit;
        }

        .fr-heading {
            font-weight: 800;
            font-size: 17px;
            margin: 0 0 8px;
        }

        .fr-note {
            font-size: 12px;
            opacity: .75;
            line-height: 1.9;
            margin: 0 0 13px;
        }

        .fr-status {
            display: inline-block;
            border-radius: 30px;
            padding: 6px 11px;
            font-size: 11px;
            background: rgba(184,145,75,.16);
            color: #e2c17e;
            margin-bottom: 12px;
        }

        .fr-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 9px;
            margin: 12px 0;
        }

        .fr-card {
            min-width: 0;
            padding: 11px;
            border: 1px solid rgba(255,255,255,.1);
            border-radius: 10px;
            background: rgba(0,0,0,.12);
        }

        .fr-card.full {
            grid-column: 1 / -1;
        }

        .fr-label {
            font-size: 11px;
            opacity: .7;
            margin-bottom: 5px;
        }

        .fr-value {
            font-size: 13px;
            line-height: 1.9;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }

        .fr-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 14px;
        }

        .fr-btn {
            border: 0;
            border-radius: 10px;
            padding: 10px 13px;
            cursor: pointer;
            font: inherit;
            font-size: 13px;
            font-weight: 700;
            background: #b8914b;
            color: #151515;
        }

        .fr-btn.secondary {
            background: rgba(255,255,255,.1);
            color: inherit;
            border: 1px solid rgba(255,255,255,.14);
        }

        .fr-btn.success {
            background: #276c5b;
            color: #fff;
        }

        .fr-btn:disabled {
            opacity: .55;
            cursor: wait;
        }

        .fr-form {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 12px;
        }

        .fr-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-width: 0;
        }

        .fr-field.full,
        .fr-map,
        .fr-coordinates,
        .fr-map-note {
            grid-column: 1 / -1;
        }

        .fr-field label {
            font-size: 12px;
            font-weight: 700;
            opacity: .85;
        }

        .fr-field input,
        .fr-field textarea,
        .fr-field select {
            width: 100%;
            box-sizing: border-box;
            border-radius: 9px;
            padding: 10px;
            border: 1px solid rgba(255,255,255,.18);
            background: rgba(0,0,0,.22);
            color: inherit;
            font: inherit;
            font-size: 13px;
            outline: none;
        }

        .fr-field textarea {
            min-height: 105px;
            resize: vertical;
            line-height: 1.9;
        }

        .fr-field select option {
            color: #111;
        }

        .fr-map {
            height: 255px;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,.16);
            background: #e5e5e5;
        }

        .fr-coordinates {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }

        .fr-map-note,
        .fr-alert {
            font-size: 11px;
            opacity: .75;
            line-height: 1.8;
        }

        .fr-alert {
            margin-top: 9px;
            min-height: 18px;
            color: #e2c17e;
        }

        .fr-empty {
            padding: 24px;
            text-align: center;
            color: var(--muted);
            line-height: 2;
        }

        .fr-empty-icon {
            font-size: 31px;
            margin-bottom: 8px;
        }

        @media(max-width:560px) {
            .fr-grid,
            .fr-form {
                grid-template-columns: 1fr;
            }

            .fr-card.full,
            .fr-field.full,
            .fr-map,
            .fr-coordinates,
            .fr-map-note {
                grid-column: 1;
            }

            .fr-map {
                height: 230px;
            }

            .fr-btn {
                flex: 1 1 45%;
            }
        }

        @media print {
            .fr-tools {
                display: none !important;
            }
        }
    `;

    document.head.appendChild(styles);

    let activeReport = null;
    let leafletPromise = null;
    let pdfPromise = null;

    function getSessionId() {
        const value =
            window.faheemActiveSessionId ||
            window.getFaheemSessionId?.() ||
            localStorage.getItem(SESSION_KEY);

        return value && value !== "null" && value !== "undefined"
            ? value
            : null;
    }

    function clean(value) {
        return String(value ?? "").trim();
    }

    function escapeHtml(value) {
        return clean(value).replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }[character]));
    }

    function locationOf(report) {
        return report?.location && typeof report.location === "object"
            ? report.location
            : {};
    }

    function descriptionOf(report) {
        return clean(
            report?.description_original ||
            report?.issue_description ||
            report?.original_text
        );
    }

    function areaOf(report) {
        const location = locationOf(report);

        return clean(
            location.area_ar ||
            location.area_ar_candidate ||
            location.area ||
            location.area_en_candidate
        );
    }

    function landmarkOf(report) {
        const location = locationOf(report);

        if (location.landmark_candidate) {
            return clean(location.landmark_candidate);
        }

        const value = location.landmarks_ar || location.landmarks || [];

        return Array.isArray(value)
            ? value.filter(Boolean).join("، ")
            : clean(value);
    }

    function directionOf(report) {
        const location = locationOf(report);

        if (location.directional_cue) {
            return clean(location.directional_cue);
        }

        return Array.isArray(location.directions)
            ? clean(location.directions[0])
            : clean(location.directions);
    }

    function durationOf(report) {
        return clean(report?.duration_ar || report?.duration);
    }

    function categoryOf(report) {
        return clean(report?.category);
    }

    function subcategoryOf(report) {
        return clean(report?.subcategory);
    }

    function categoryName(report) {
        return clean(
            report?.category_ar ||
            report?.category_label_ar ||
            CATEGORY_LABELS[categoryOf(report)] ||
            "غير محدد"
        );
    }

    function subcategoryName(report) {
        return clean(
            report?.subcategory_ar ||
            report?.subcategory_label_ar ||
            SUBCATEGORIES[categoryOf(report)]?.[subcategoryOf(report)] ||
            "غير محدد"
        );
    }

    function locationName(report) {
        return [
            areaOf(report),
            directionOf(report),
            landmarkOf(report)
        ].filter(Boolean).join("، ") || "غير محدد";
    }

    function coordinatesOf(report) {
        const coordinates = locationOf(report).coordinates;

        if (Array.isArray(coordinates) && coordinates.length >= 2) {
            return {
                latitude: Number(coordinates[0]),
                longitude: Number(coordinates[1])
            };
        }

        if (coordinates && typeof coordinates === "object") {
            const latitude =
                coordinates.latitude ?? coordinates.lat;

            const longitude =
                coordinates.longitude ??
                coordinates.lon ??
                coordinates.lng ??
                coordinates.long;

            if (latitude != null && longitude != null) {
                return {
                    latitude: Number(latitude),
                    longitude: Number(longitude)
                };
            }
        }

        return null;
    }

    async function request(path, options = {}) {
        const response = await fetch(`${API}${path}`, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            }
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const detail = data.detail;

            throw new Error(
                typeof detail === "string"
                    ? detail
                    : detail?.message || `تعذر تنفيذ العملية (${response.status}).`
            );
        }

        return data;
    }

    function makeButton(label, type, callback) {
        const button = document.createElement("button");

        button.type = "button";
        button.className = `fr-btn ${type || "secondary"}`;
        button.textContent = label;
        button.addEventListener("click", callback);

        return button;
    }

    function makeField(labelText, control, full = false) {
        const wrapper = document.createElement("div");
        wrapper.className = `fr-field${full ? " full" : ""}`;

        const label = document.createElement("label");
        label.textContent = labelText;

        wrapper.append(label, control);

        return wrapper;
    }

    function makeInput(value, placeholder = "", type = "text") {
        const input = document.createElement("input");

        input.type = type;
        input.value = value || "";
        input.placeholder = placeholder;

        return input;
    }

    function makeSelect(options, value) {
        const select = document.createElement("select");

        Object.entries(options).forEach(([key, label]) => {
            const option = document.createElement("option");

            option.value = key;
            option.textContent = label;

            select.appendChild(option);
        });

        select.value = value || "";

        return select;
    }

    function showEmptyState(panel) {
        panel.replaceChildren();

        const empty = document.createElement("div");
        empty.className = "fr-empty";

        const icon = document.createElement("div");
        icon.className = "fr-empty-icon";
        icon.textContent = "📄";

        const title = document.createElement("div");
        title.textContent = "لم يتم تجهيز البلاغ بعد";

        const description = document.createElement("div");
        description.textContent =
            "أكمل وصف المشكلة وتأكيد الموقع حتى تظهر مسودة البلاغ هنا.";

        empty.append(icon, title, description);
        panel.appendChild(empty);
    }

    function renderReportView(report) {
        const panel = document.getElementById("reportContent");

        if (!panel) return;

        panel.replaceChildren();

        if (!report) {
            showEmptyState(panel);
            return;
        }

        const tools = document.createElement("section");
        tools.className = "fr-tools";

        const heading = document.createElement("h3");
        heading.className = "fr-heading";
        heading.textContent = "مراجعة مسودة البلاغ";

        const status = document.createElement("div");
        status.className = "fr-status";

        const confirmed =
            report.user_approved ||
            report.status === "confirmed_not_submitted";

        status.textContent = confirmed
            ? "تم تأكيد المسودة · لم يتم الإرسال"
            : "مسودة جاهزة للمراجعة · لم يتم الإرسال";

        const note = document.createElement("p");
        note.className = "fr-note";
        note.textContent =
            "راجع تفاصيل البلاغ. يمكنك تعديل البيانات أو تنزيل نسخة PDF أو نسخ البلاغ ومشاركته.";

        const grid = document.createElement("div");
        grid.className = "fr-grid";

        function addCard(label, value, full = false) {
            const card = document.createElement("div");
            card.className = `fr-card${full ? " full" : ""}`;

            const title = document.createElement("div");
            title.className = "fr-label";
            title.textContent = label;

            const content = document.createElement("div");
            content.className = "fr-value";
            content.textContent = value || "غير محدد";

            card.append(title, content);
            grid.appendChild(card);
        }

        const coordinates = coordinatesOf(report);

        addCard("رقم البلاغ", report.report_id || "غير محدد");
        addCard("التصنيف", categoryName(report));
        addCard("نوع المشكلة", subcategoryName(report));
        addCard("مدة المشكلة", durationOf(report) || "غير محددة");
        addCard("الموقع", locationName(report), true);
        addCard("وصف المشكلة", descriptionOf(report), true);

        addCard(
            "الإحداثيات",
            coordinates
                ? `${coordinates.latitude}, ${coordinates.longitude}`
                : "لم يتم تحديد نقطة على الخريطة",
            true
        );

        const actions = document.createElement("div");
        actions.className = "fr-actions";

        actions.append(
            makeButton(
                "تعديل البيانات",
                "",
                () => openEditor(report)
            ),
            makeButton(
                "تنزيل PDF",
                "secondary",
                () => downloadPdf(report)
            ),
            makeButton(
                "نسخ نص البلاغ",
                "secondary",
                () => copyReport(report)
            ),
            makeButton(
                "مشاركة",
                "secondary",
                () => shareReport(report)
            )
        );

        const confirmButton = makeButton(
            confirmed ? "تم تأكيد المسودة" : "تأكيد النسخة النهائية",
            "success",
            () => confirmReport(report)
        );

        confirmButton.disabled = Boolean(confirmed);
        actions.appendChild(confirmButton);

        const disclaimer = document.createElement("p");
        disclaimer.className = "fr-note";
        disclaimer.style.marginTop = "13px";
        disclaimer.textContent =
            "تنبيه: تأكيد المسودة يحفظ موافقتك داخل النموذج فقط. لا يتم إرسال البلاغ إلى أي جهة حكومية.";

        tools.append(
            heading,
            status,
            note,
            grid,
            actions,
            disclaimer
        );

        panel.appendChild(tools);
    }

    function renderReview(payload) {
        const report = payload?.report || payload;

        if (
            !report ||
            !report.report_id ||
            report.ready_for_review !== true
        ) {
            activeReport = null;
            renderReportView(null);
            return;
        }

        activeReport = report;
        renderReportView(report);
    }

    window.faheemRenderReportReview = renderReview;

    function populateSubcategories(category, select, selected) {
        select.replaceChildren();

        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = "غير محدد";
        select.appendChild(empty);

        Object.entries(SUBCATEGORIES[category.value] || {}).forEach(
            ([key, label]) => {
                const option = document.createElement("option");

                option.value = key;
                option.textContent = label;

                select.appendChild(option);
            }
        );

        if (
            Object.hasOwn(
                SUBCATEGORIES[category.value] || {},
                selected
            )
        ) {
            select.value = selected;
        }
    }

    async function openEditor(report) {
        const panel = document.getElementById("reportContent");

        if (!panel) return;

        panel.replaceChildren();

        const tools = document.createElement("section");
        tools.className = "fr-tools";

        const heading = document.createElement("h3");
        heading.className = "fr-heading";
        heading.textContent = "تعديل بيانات البلاغ";

        const note = document.createElement("p");
        note.className = "fr-note";
        note.textContent =
            "عدّل المعلومات ثم اضغط حفظ. يمكنك تغيير الموقع وإضافة معلم قريب أو تحديد نقطة اختيارية على الخريطة.";

        const form = document.createElement("div");
        form.className = "fr-form";

        const description = document.createElement("textarea");
        description.value = descriptionOf(report);
        description.placeholder = "اكتب وصف المشكلة";

        form.appendChild(
            makeField("وصف المشكلة", description, true)
        );

        const category = makeSelect(
            CATEGORY_LABELS,
            categoryOf(report) || "road_infrastructure"
        );

        const subcategory = document.createElement("select");

        populateSubcategories(
            category,
            subcategory,
            subcategoryOf(report)
        );

        category.addEventListener("change", () => {
            populateSubcategories(
                category,
                subcategory,
                ""
            );
        });

        form.append(
            makeField("التصنيف", category),
            makeField("نوع المشكلة", subcategory)
        );

        const duration = makeInput(
            durationOf(report),
            "مثال: منذ ثلاثة أيام"
        );

        const area = makeInput(
            areaOf(report),
            "اسم المنطقة أو الحي"
        );

        const landmark = makeInput(
            landmarkOf(report),
            "مثال: المدرسة أو المسجد"
        );

        const direction = makeInput(
            directionOf(report),
            "مثال: بجوار أو مقابل أو خلف"
        );

        form.append(
            makeField("مدة المشكلة", duration),
            makeField("المنطقة / الحي", area),
            makeField("أقرب معلم معروف", landmark),
            makeField("الاتجاه أو العلاقة بالمعلم", direction)
        );

        const mapNote = document.createElement("div");
        mapNote.className = "fr-map-note";
        mapNote.textContent =
            "اختياري: انقر على الخريطة لتحديد مكان المشكلة أو اسحب العلامة لتعديل الموقع. لن نطلب إذن الوصول إلى موقع جهازك.";

        form.appendChild(mapNote);

        const mapBox = document.createElement("div");
        mapBox.className = "fr-map";
        mapBox.id = "faheemReportMap";

        form.appendChild(mapBox);

        const currentCoordinates = coordinatesOf(report);

        const mapLat = currentCoordinates?.latitude || 24.4539;
        const mapLon = currentCoordinates?.longitude || 54.3773;
        const hasCoordinates = Boolean(currentCoordinates);

        const latitude = makeInput(
            hasCoordinates ? mapLat.toFixed(6) : "",
            "24.453900",
            "number"
        );

        const longitude = makeInput(
            hasCoordinates ? mapLon.toFixed(6) : "",
            "54.377300",
            "number"
        );

        latitude.step = "0.000001";
        longitude.step = "0.000001";

        const coordinateFields = document.createElement("div");
        coordinateFields.className = "fr-coordinates";

        coordinateFields.append(
            makeField("خط العرض", latitude),
            makeField("خط الطول", longitude)
        );

        form.appendChild(coordinateFields);

        const alertElement = document.createElement("div");
        alertElement.className = "fr-alert";
        alertElement.textContent =
            "يمكنك حفظ البلاغ دون إحداثيات؛ تحديد نقطة على الخريطة اختياري.";

        const actions = document.createElement("div");
        actions.className = "fr-actions";

        const saveButton = makeButton(
            "حفظ التعديلات",
            "success",
            async () => {
                const sid = getSessionId();

                if (!sid) {
                    alertElement.textContent =
                        "تعذر العثور على جلسة البلاغ. ابدأ بلاغاً جديداً.";
                    return;
                }

                if (!description.value.trim()) {
                    alertElement.textContent =
                        "يرجى إدخال وصف المشكلة.";
                    return;
                }

                if (
                    (latitude.value.trim() && !longitude.value.trim()) ||
                    (!latitude.value.trim() && longitude.value.trim())
                ) {
                    alertElement.textContent =
                        "أدخل خط العرض وخط الطول معاً، أو اتركهما فارغين.";
                    return;
                }

                const lat = latitude.value.trim()
                    ? Number(latitude.value)
                    : null;

                const lon = longitude.value.trim()
                    ? Number(longitude.value)
                    : null;

                if (
                    lat !== null &&
                    (
                        !Number.isFinite(lat) ||
                        !Number.isFinite(lon) ||
                        lat < 22 ||
                        lat > 27 ||
                        lon < 51 ||
                        lon > 57.5
                    )
                ) {
                    alertElement.textContent =
                        "الإحداثيات المدخلة خارج النطاق الجغرافي المتوقع لدولة الإمارات.";
                    return;
                }

                saveButton.disabled = true;
                alertElement.textContent = "جارٍ حفظ التعديلات...";

                try {
                    const coordinates = lat !== null
                        ? {
                            latitude: lat,
                            longitude: lon
                        }
                        : null;

                    const result = await request(
                        `/api/reports/${encodeURIComponent(sid)}`,
                        {
                            method: "PATCH",
                            body: JSON.stringify({
                                description: description.value.trim(),
                                category: category.value,
                                subcategory: subcategory.value || null,
                                duration: duration.value.trim(),
                                area: area.value.trim(),
                                landmark: landmark.value.trim(),
                                direction: direction.value.trim(),
                                coordinates
                            })
                        }
                    );

                    activeReport = result.report;
                    renderReportView(activeReport);

                } catch (error) {
                    alertElement.textContent = error.message;
                } finally {
                    saveButton.disabled = false;
                }
            }
        );

        actions.append(
            saveButton,
            makeButton(
                "إلغاء",
                "secondary",
                () => renderReportView(report)
            )
        );

        tools.append(
            heading,
            note,
            form,
            alertElement,
            actions
        );

        panel.appendChild(tools);

        try {
            await loadLeaflet();

            if (!document.getElementById("faheemReportMap")) {
                return;
            }

            const map = window.L.map("faheemReportMap").setView(
                [mapLat, mapLon],
                hasCoordinates ? 16 : 11
            );

            window.L.tileLayer(
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                {
                    maxZoom: 19,
                    attribution: "&copy; OpenStreetMap contributors"
                }
            ).addTo(map);

            let marker = null;

            const setPoint = point => {
                latitude.value = point.lat.toFixed(6);
                longitude.value = point.lng.toFixed(6);

                if (!marker) {
                    marker = window.L.marker(point, {
                        draggable: true
                    }).addTo(map);

                    marker.on("dragend", event => {
                        setPoint(event.target.getLatLng());
                    });
                } else {
                    marker.setLatLng(point);
                }
            };

            if (hasCoordinates) {
                setPoint({
                    lat: mapLat,
                    lng: mapLon
                });
            }

            map.on("click", event => {
                setPoint(event.latlng);
            });

            requestAnimationFrame(() => map.invalidateSize());

        } catch (error) {
            mapBox.textContent =
                "تعذر تحميل الخريطة. يمكنك إدخال خط العرض وخط الطول يدوياً.";

            mapBox.style.display = "grid";
            mapBox.style.placeItems = "center";
            mapBox.style.padding = "14px";
            mapBox.style.boxSizing = "border-box";
            mapBox.style.color = "#222";
        }
    }

    function loadLeaflet() {
        if (window.L) return Promise.resolve();
        if (leafletPromise) return leafletPromise;

        leafletPromise = new Promise((resolve, reject) => {
            if (!document.getElementById("faheem-leaflet-css")) {
                const css = document.createElement("link");

                css.id = "faheem-leaflet-css";
                css.rel = "stylesheet";
                css.href =
                    "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";

                document.head.appendChild(css);
            }

            const existing = document.getElementById("faheem-leaflet-js");

            if (existing) {
                existing.addEventListener("load", resolve, { once: true });
                existing.addEventListener("error", reject, { once: true });
                return;
            }

            const script = document.createElement("script");

            script.id = "faheem-leaflet-js";
            script.src =
                "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";

            script.onload = resolve;
            script.onerror = reject;

            document.head.appendChild(script);
        });

        return leafletPromise;
    }

    function reportText(report) {
        const location = locationOf(report);
        const coordinates = coordinatesOf(report);

        const coordinateText = coordinates
            ? `${coordinates.latitude}, ${coordinates.longitude}`
            : "غير محددة";

        return [
            "ملخص البلاغ المدني",
            "━━━━━━━━━━━━━━━━━━",
            `رقم البلاغ: ${report.report_id || "غير محدد"}`,
            `التصنيف: ${categoryName(report)}`,
            `نوع المشكلة: ${subcategoryName(report)}`,
            "",
            "وصف المشكلة:",
            descriptionOf(report) || "غير محدد",
            "",
            "الموقع:",
            areaOf(report) || "غير محدد",
            `أقرب معلم: ${landmarkOf(report) || "غير محدد"}`,
            `الاتجاه: ${directionOf(report) || "غير محدد"}`,
            `الإحداثيات: ${coordinateText}`,
            "",
            `مدة المشكلة: ${durationOf(report) || "غير محددة"}`,
            `تأكيد الموقع: ${
                location.user_confirmed || location.confirmed
                    ? "تم التأكيد من المستخدم؛ لم يتم التحقق الجغرافي"
                    : "بانتظار التأكيد"
            }`,
            `حالة البلاغ: ${
                report.user_approved ||
                report.status === "confirmed_not_submitted"
                    ? "تم تأكيد المسودة"
                    : "مسودة للمراجعة"
            }`,
            "حالة الإرسال: مسودة — لم يتم إرسال البلاغ"
        ].join("\n");
    }

    async function copyReport(report) {
        const value = reportText(report);

        try {
            await navigator.clipboard.writeText(value);
            alert("تم نسخ نص البلاغ.");
        } catch (error) {
            const element = document.createElement("textarea");

            element.value = value;
            document.body.appendChild(element);
            element.select();
            document.execCommand("copy");
            element.remove();

            alert("تم نسخ نص البلاغ.");
        }
    }

    async function shareReport(report) {
        const value = reportText(report);

        if (navigator.share) {
            try {
                await navigator.share({
                    title: "بلاغ FAHEEM AI",
                    text: value
                });

                return;
            } catch (error) {
                if (error.name === "AbortError") return;
            }
        }

        await copyReport(report);
    }

    function loadPdfLibrary() {
        if (window.html2pdf) return Promise.resolve();
        if (pdfPromise) return pdfPromise;

        pdfPromise = new Promise((resolve, reject) => {
            const script = document.createElement("script");

            script.src =
                "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";

            script.onload = resolve;
            script.onerror = reject;

            document.head.appendChild(script);
        });

        return pdfPromise;
    }

    function pdfMarkup(report) {
        const coordinates = coordinatesOf(report);

        const coordinateText = coordinates
            ? `${coordinates.latitude}, ${coordinates.longitude}`
            : "غير محددة";

        const rows = [
            ["رقم البلاغ", report.report_id],
            ["التصنيف", categoryName(report)],
            ["نوع المشكلة", subcategoryName(report)],
            ["الموقع", locationName(report)],
            ["أقرب معلم", landmarkOf(report) || "غير محدد"],
            ["الاتجاه", directionOf(report) || "غير محدد"],
            ["الإحداثيات", coordinateText],
            ["مدة المشكلة", durationOf(report) || "غير محددة"]
        ];

        const rowMarkup = rows.map(([label, value]) => `
            <div style="
                display:flex;
                gap:14px;
                border-bottom:1px solid #e4e7eb;
                padding:10px 0;
                align-items:flex-start;
            ">
                <strong style="width:155px;flex-shrink:0">
                    ${escapeHtml(label)}
                </strong>
                <span style="flex:1;overflow-wrap:anywhere">
                    ${escapeHtml(value || "غير محدد")}
                </span>
            </div>
        `).join("");

        return `
            <div dir="rtl" style="
                font-family:Tahoma,Arial,sans-serif;
                color:#17202b;
                line-height:1.9;
                direction:rtl;
                text-align:right;
            ">
                <div style="
                    border-bottom:3px solid #b8914b;
                    padding-bottom:18px;
                    margin-bottom:18px;
                ">
                    <div style="
                        font-size:13px;
                        color:#8b6a2f;
                        font-weight:bold;
                    ">
                        FAHEEM AI · أبوظبي
                    </div>

                    <h1 style="font-size:26px;margin:8px 0">
                        ملخص البلاغ المدني
                    </h1>

                    <div style="font-size:13px;color:#667085">
                        مسودة أعدّها المستخدم للمراجعة
                    </div>
                </div>

                ${rowMarkup}

                <h2 style="font-size:18px;margin:24px 0 8px">
                    وصف المشكلة
                </h2>

                <div style="
                    white-space:pre-wrap;
                    background:#f6f7f9;
                    padding:16px;
                    border-radius:10px;
                ">
                    ${escapeHtml(descriptionOf(report) || "غير محدد")}
                </div>

                <div style="
                    margin-top:28px;
                    padding:14px;
                    background:#fff8e8;
                    border:1px solid #ead7a8;
                    border-radius:10px;
                    font-size:13px;
                ">
                    حالة الإرسال: مسودة — لم يتم إرسال البلاغ إلى أي جهة حكومية.
                </div>
            </div>
        `;
    }

    async function downloadPdf(report) {
    let root = null;
    let printWindow = null;

    const previousScrollX = window.scrollX;
    const previousScrollY = window.scrollY;

    try {
        await loadPdfLibrary();

        root = document.createElement("div");

        root.style.cssText = `
            position:relative;
            display:block;
            width:794px;
            max-width:none;
            margin:24px auto;
            padding:42px;
            background:#ffffff;
            color:#17202b;
            z-index:999999;
            box-sizing:border-box;
            font-family:Tahoma,Arial,sans-serif;
            font-size:14px;
            line-height:1.9;
            direction:rtl;
            text-align:right;
        `;

        root.innerHTML = pdfMarkup(report);
        document.body.appendChild(root);

        if (document.fonts?.ready) {
            await document.fonts.ready;
        }

        await new Promise(resolve => {
            requestAnimationFrame(() => {
                requestAnimationFrame(resolve);
            });
        });

        root.scrollIntoView({
            behavior: "instant",
            block: "center"
        });

        await new Promise(resolve => {
            requestAnimationFrame(resolve);
        });

        const filename = (
            String(report.report_id || "FAHEEM-report")
                .replace(/[^a-zA-Z0-9_-]/g, "-")
        ) + ".pdf";

        await window.html2pdf()
            .set({
                margin: [10, 10, 10, 10],
                filename,
                image: {
                    type: "jpeg",
                    quality: 1
                },
                html2canvas: {
                    scale: 2,
                    useCORS: true,
                    allowTaint: false,
                    backgroundColor: "#ffffff",
                    logging: false,
                    scrollX: 0,
                    scrollY: 0,
                    windowWidth: 1000
                },
                jsPDF: {
                    unit: "mm",
                    format: "a4",
                    orientation: "portrait"
                },
                pagebreak: {
                    mode: ["css", "legacy"]
                }
            })
            .from(root)
            .save();

        alert("تم تنزيل تقرير FAHEEM بصيغة PDF بنجاح.");

    } catch (error) {
        console.error("PDF generation failed:", error);

        printWindow = window.open("", "_blank");

        if (!printWindow) {
            alert(
                "تعذر إنشاء PDF. اسمح بالنوافذ المنبثقة وحاول مرة أخرى."
            );
            return;
        }

        printWindow.document.open();

        printWindow.document.write(`
            <!DOCTYPE html>
            <html lang="ar" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <title>FAHEEM ${escapeHtml(report.report_id)}</title>
                <style>
                    @page {
                        size: A4;
                        margin: 15mm;
                    }

                    body {
                        font-family: Tahoma, Arial, sans-serif;
                        padding: 20px;
                        line-height: 1.9;
                        direction: rtl;
                        text-align: right;
                        color: #17202b;
                    }

                    h1 {
                        border-bottom: 3px solid #b8914b;
                        padding-bottom: 12px;
                    }

                    .note {
                        margin-top: 25px;
                        padding: 14px;
                        background: #fff8e8;
                        border: 1px solid #ead7a8;
                    }
                </style>
            </head>
            <body>
                ${pdfMarkup(report)}

                <script>
                    window.onload = () => {
                        setTimeout(() => window.print(), 500);
                    };
                <\/script>
            </body>
            </html>
        `);

        printWindow.document.close();

    } finally {
        root?.remove();

        window.scrollTo(
            previousScrollX,
            previousScrollY
        );
    }
}

    async function confirmReport(report) {
        const sid = getSessionId();

        if (!sid) {
            alert("تعذر العثور على جلسة البلاغ.");
            return;
        }

        if (
            !descriptionOf(report) ||
            !categoryOf(report) ||
            !(areaOf(report) || landmarkOf(report) || coordinatesOf(report))
        ) {
            alert("أكمل الوصف والتصنيف والموقع قبل التأكيد.");
            return;
        }

        const approved = window.confirm(
            "هل تؤكد أن هذه هي النسخة النهائية؟ لن يتم إرسالها إلى أي جهة حكومية."
        );

        if (!approved) return;

        try {
            const result = await request(
                `/api/reports/${encodeURIComponent(sid)}/confirm`,
                {
                    method: "POST",
                    body: "{}"
                }
            );

            activeReport = result.report;
            renderReportView(activeReport);

            alert(
                result.message_ar ||
                "تم تأكيد مسودة البلاغ. لم يتم إرسالها إلى أي جهة."
            );

        } catch (error) {
            alert(error.message);
        }
    }

    renderReview(null);
})();