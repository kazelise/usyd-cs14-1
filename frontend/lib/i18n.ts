export type Locale = "en" | "zh";

export const dict = {
  en: {
    title: "Study Participation",
    subtitle: "Please read the info below before starting.",
    estTime: "Estimated duration",
    consent: "By clicking Start, you consent to participate and agree to anonymized data collection for research purposes.",
    start: "Start",
    minutes: "minutes",
    language: "Language",
    like: "👍 Like",
    liked: "👍 Liked",
    comment: "💬 Comment",
    writeComment: "Write a comment...",
    complete: "Complete Survey",
    thankYou: "Thank you!",
    recorded: "Your responses have been recorded.",
    comments: "comments",
    shares: "shares",
    // Calibration
    calibCameraAccess: "Camera Access",
    calibFaceAlignment: "Face Alignment",
    calibEyeTracking: "Eye Tracking",
    calibSummary: "Calibration Summary",
    calibAllowCamera: "Allow camera access to begin calibration.",
    calibCenterFace: "Center your face in the frame and keep still.",
    calibFollowDot: "Follow the active dot with your eyes only.",
    calibFinished: "Calibration finished. Review the capture quality.",
    calibRetry: "Retry Calibration",
    calibContinue: "Continue to Survey",
    calibFaceDetected: "Face detected",
    calibSearching: "Searching for face",
    // Tracking indicators
    gazeTrackingActive: "Gaze tracking active",
    clickTrackingActive: "Click tracking active",
    calibrationCompleted: "Calibration completed",
    // Questions
    submitAnswer: "Submit Answer",
    answerSubmitted: "Answer submitted",
    questions: "Questions",
    typeYourAnswer: "Type your answer...",
  },
  zh: {
    title: "实验参与",
    subtitle: "开始前请阅读以下信息。",
    estTime: "预计时长",
    consent: "点击开始即表示您同意参与本研究，并同意我们以匿名方式收集数据用于科研。",
    start: "开始",
    minutes: "分钟",
    language: "语言",
    like: "👍 赞",
    liked: "👍 已赞",
    comment: "💬 评论",
    writeComment: "写下你的评论...",
    complete: "完成问卷",
    thankYou: "感谢参与！",
    recorded: "您的回答已记录。",
    comments: "条评论",
    shares: "次分享",
    // Calibration
    calibCameraAccess: "摄像头权限",
    calibFaceAlignment: "面部对齐",
    calibEyeTracking: "眼动追踪",
    calibSummary: "校准结果",
    calibAllowCamera: "请允许摄像头访问以开始校准。",
    calibCenterFace: "请将面部置于画面中央并保持不动。",
    calibFollowDot: "请仅用眼睛跟踪活跃的圆点。",
    calibFinished: "校准完成。请查看采集质量。",
    calibRetry: "重新校准",
    calibContinue: "继续填写问卷",
    calibFaceDetected: "已检测到人脸",
    calibSearching: "正在搜索人脸",
    // Tracking indicators
    gazeTrackingActive: "眼动追踪进行中",
    clickTrackingActive: "点击追踪进行中",
    calibrationCompleted: "校准已完成",
    // Questions
    submitAnswer: "提交回答",
    answerSubmitted: "回答已提交",
    questions: "问题",
    typeYourAnswer: "请输入你的回答...",
  },
} as const;

export function t(locale: Locale, key: keyof typeof dict["en"]) {
  return dict[locale][key];
}

