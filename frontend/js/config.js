/* API 주소 결정
 * - Netlify(1단계 프런트엔드 단독 배포) / 파일 직접 열기 → Render 백엔드 API
 * - Render·EC2·로컬(FastAPI 가 프런트엔드를 함께 제공) → 같은 도메인의 /api/v1
 * - localStorage 'np_api_base' 로 수동 지정 가능
 */
window.NP_CONFIG = (() => {
  const RENDER_API = "https://nomadpick.onrender.com/api/v1";
  const host = location.hostname;
  const standalone = location.protocol === "file:" || host.endsWith("netlify.app") || location.port === "5500";
  return {
    API_BASE: localStorage.getItem("np_api_base") || (standalone ? RENDER_API : "/api/v1"),
    SAMPLE_DATA: "data/sample-products.json",
    REQUEST_TIMEOUT_MS: 15000,
  };
})();
