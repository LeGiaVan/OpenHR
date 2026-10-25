import { useEffect, useMemo, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export default function App() {
  const [config, setConfig] = useState(null);
  const [apiState, setApiState] = useState("loading");
  const [apiMessage, setApiMessage] = useState("");
  const [language, setLanguage] = useState("vi");
  const [levelId, setLevelId] = useState("");
  const [pressureId, setPressureId] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    fetch(API_BASE + "/config", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("API trả về trạng thái " + response.status);
        }
        return response.json();
      })
      .then((data) => {
        setConfig(data);
        setLevelId(data.default_level);
        setPressureId(data.default_pressure_profile);
        setApiState("connected");
        setApiMessage("");
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setApiState("error");
        setApiMessage(error.message || "Không thể tải cấu hình từ API.");
      });

    return () => controller.abort();
  }, []);

  const selectedLevel = useMemo(
    () => config?.levels.find((level) => level.id === levelId),
    [config, levelId],
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="OpenHR trang chủ">
          <span className="brand-mark">O</span>
          <span>
            <strong>openhr</strong>
            <small>INTERVIEW PRACTICE</small>
          </span>
        </a>
        <div className="topbar-right">
          <span className="topbar-label">BẢN THỬ NGHIỆM</span>
          <div className={"connection " + apiState}>
            <span className="connection-dot" />
            {apiState === "connected"
              ? "API đã kết nối"
              : apiState === "loading"
                ? "Đang kết nối"
                : "API chưa sẵn sàng"}
          </div>
        </div>
      </header>

      <main className="page-content">
        <section className="intro">
          <div className="eyebrow">
            <span className="eyebrow-line" />
            YOUR NEXT INTERVIEW STARTS HERE
          </div>
          <h1>
            Tập dượt hôm nay.
            <br />
            <em>Tự tin ngày mai.</em>
          </h1>
          <p className="intro-copy">
            Một buổi phỏng vấn thử được cá nhân hóa theo hồ sơ và vị trí bạn
            đang hướng đến.
          </p>
        </section>

        <div className="stepper" aria-label="Các bước">
          <Step number="01" label="Hồ sơ & công việc" active />
          <span className="step-connector" />
          <Step number="02" label="Thiết lập buổi tập" />
          <span className="step-connector" />
          <Step number="03" label="Phỏng vấn & phản hồi" />
        </div>

        {apiState === "error" && (
          <div className="notice notice-error" role="alert">
            <strong>Chưa tải được cấu hình.</strong>
            <span>{apiMessage} Hãy khởi động backend rồi tải lại trang.</span>
          </div>
        )}

        <div className="setup-grid">
          <section className="panel documents-panel">
            <div className="panel-heading">
              <div>
                <span className="section-index">01 / CONTEXT</span>
                <h2>Cho AI biết về bạn</h2>
              </div>
              <span className="required-tag">CẦN CÓ CẢ HAI</span>
            </div>
            <p className="panel-copy">
              Hồ sơ và mô tả công việc giúp câu hỏi bám sát trải nghiệm cùng
              vị trí ứng tuyển của bạn.
            </p>
            <div className="upload-list">
              <UploadCard
                label="CV của bạn"
                detail="Kinh nghiệm, dự án và kỹ năng"
              />
              <UploadCard
                label="Mô tả công việc"
                detail="JD của vị trí bạn đang ứng tuyển"
              />
            </div>
            <div className="file-note">
              <span className="file-note-icon">i</span>
              <span>
                POC nhận PDF và DOCX có text. Tài liệu scan chưa được hỗ trợ.
              </span>
            </div>
          </section>

          <section className="panel settings-panel">
            <div className="panel-heading">
              <div>
                <span className="section-index">02 / SESSION</span>
                <h2>Thiết lập buổi tập</h2>
              </div>
              <span className="config-tag">
                {config ? "ĐÃ TẢI TỪ API" : "CHỜ CẤU HÌNH"}
              </span>
            </div>

            <fieldset className="field-group">
              <legend>Ngôn ngữ phỏng vấn</legend>
              <div className="language-options">
                {config?.languages.map((option) => (
                  <button
                    className={
                      "choice-button" +
                      (language === option.code ? " selected" : "")
                    }
                    key={option.code}
                    type="button"
                    onClick={() => setLanguage(option.code)}
                    disabled={!config}
                  >
                    <span className="choice-radio" />
                    {option.label}
                  </button>
                ))}
                {!config && <span className="loading-inline">Đang tải…</span>}
              </div>
            </fieldset>

            <label className="field-group select-field">
              <span>Cấp độ phỏng vấn</span>
              <select
                value={levelId}
                onChange={(event) => setLevelId(event.target.value)}
                disabled={!config}
              >
                {config?.levels.map((level) => (
                  <option key={level.id} value={level.id}>
                    {level.name} · {level.difficulty}
                  </option>
                ))}
              </select>
            </label>

            {selectedLevel && (
              <div className="level-preview">
                <div className="mix-heading">
                  <span>NỘI DUNG BUỔI TẬP</span>
                  <span>{selectedLevel.id.toUpperCase()}</span>
                </div>
                <div className="mix-bar" aria-label="Tỷ lệ câu hỏi">
                  <span
                    className="mix-behavioral"
                    style={{
                      width:
                        selectedLevel.question_mix.behavioral * 100 + "%",
                    }}
                  />
                  <span
                    className="mix-role"
                    style={{
                      width:
                        selectedLevel.question_mix.role_specific * 100 + "%",
                    }}
                  />
                </div>
                <div className="mix-legend">
                  <span>
                    <i className="legend-dot behavioral-dot" />
                    Behavioral{" "}
                    {Math.round(selectedLevel.question_mix.behavioral * 100)}%
                  </span>
                  <span>
                    <i className="legend-dot role-dot" />
                    Chuyên môn{" "}
                    {Math.round(selectedLevel.question_mix.role_specific * 100)}
                    %
                  </span>
                </div>
              </div>
            )}

            <label className="field-group select-field pressure-field">
              <span>Mức áp lực</span>
              <select
                value={pressureId}
                onChange={(event) => setPressureId(event.target.value)}
                disabled={!config}
              >
                {Object.entries(config?.pressure_profiles ?? {}).map(
                  ([id, profile]) => (
                    <option key={id} value={id}>
                      {id} · {profile.description}
                    </option>
                  ),
                )}
              </select>
              <small>
                Thời lượng từng câu được phân bổ theo độ khó từ cấu hình.
              </small>
            </label>
          </section>
        </div>

        <section className="bottom-row">
          <div className="phase-note">
            <span className="phase-note-symbol">✳</span>
            <p>
              <strong>Đang xây nền tảng cho buổi tập của bạn.</strong>
              <br />
              Tải CV/JD và phòng phỏng vấn sẽ được nối ở các phase tiếp theo.
            </p>
          </div>
          <button className="start-button" type="button" disabled>
            Bắt đầu phỏng vấn <span aria-hidden="true">↗</span>
          </button>
        </section>

        <footer className="page-footer">
          <span>OPENHR INTERVIEW PRACTICE</span>
          <span>Thực hành để tiến bộ, không phải để được chấm đậu/rớt.</span>
        </footer>
      </main>
    </div>
  );
}

function Step({ number, label, active = false }) {
  return (
    <div className={"step" + (active ? " active" : "")}>
      <span className="step-number">{number}</span>
      <span>{label}</span>
    </div>
  );
}

function UploadCard({ label, detail }) {
  return (
    <div className="upload-card disabled" aria-disabled="true">
      <div className="upload-icon" aria-hidden="true">
        +
      </div>
      <div className="upload-text">
        <strong>{label}</strong>
        <span>{detail}</span>
      </div>
      <span className="upload-status">SẮP CÓ</span>
    </div>
  );
}
