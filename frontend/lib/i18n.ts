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
  },
} as const;

export function t(locale: Locale, key: keyof typeof dict["en"]) {
  return dict[locale][key];
}

