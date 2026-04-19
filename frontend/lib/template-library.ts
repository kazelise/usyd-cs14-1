export type TemplateCommentSnapshot = {
  author_name: string;
  text: string;
};

export type TemplatePostSnapshot = {
  original_url: string;
  display_title: string | null;
  display_image_url: string | null;
  display_likes: number;
  display_comments_count: number;
  display_shares: number;
  show_likes: boolean;
  show_comments: boolean;
  show_shares: boolean;
  visible_to_groups: number[] | null;
  group_overrides: Record<string, { display_likes: number; display_comments_count: number; display_shares: number }> | null;
  comments: TemplateCommentSnapshot[];
};

export type TemplateDefinition = {
  id: string;
  source: "built_in" | "saved";
  name: string;
  category: string;
  summary: string;
  groups: number;
  postSlots: number;
  questionBlocks: number;
  tags: string[];
  setup: {
    title: string;
    description: string;
    num_groups: number;
    gaze_tracking_enabled: boolean;
    gaze_interval_ms?: number;
    click_tracking_enabled: boolean;
    calibration_enabled: boolean;
    calibration_points: number;
  };
  conditionNotes: string[];
  suggestedFlow: string[];
  posts?: TemplatePostSnapshot[];
};

const STORAGE_KEY = "cs14-saved-templates";

export const defaultTemplateLibrary: TemplateDefinition[] = [
  {
    id: "news-credibility-ab",
    source: "built_in",
    name: "News Credibility A/B",
    category: "News",
    summary: "Compare engagement when social proof is visible versus hidden across the same article set.",
    groups: 2,
    postSlots: 5,
    questionBlocks: 8,
    tags: ["A/B", "Tracking", "Questions"],
    setup: {
      title: "News Credibility A/B Study",
      description: "Evaluate how visible social proof changes click behaviour and trust ratings across equivalent news posts.",
      num_groups: 2,
      gaze_tracking_enabled: true,
      click_tracking_enabled: true,
      calibration_enabled: true,
      calibration_points: 9,
    },
    conditionNotes: ["Group 1 sees likes and comments", "Group 2 sees identical posts with social proof reduced"],
    suggestedFlow: [
      "Paste 5 article URLs from the same topic cluster.",
      "Configure one trust-rating question block after each post.",
      "Compare click-through and credibility scores by group.",
    ],
  },
  {
    id: "source-trust-study",
    source: "built_in",
    name: "Source Trust Template",
    category: "Trust",
    summary: "Test whether source visibility and familiarity change reading behaviour and post-level trust.",
    groups: 2,
    postSlots: 4,
    questionBlocks: 6,
    tags: ["A/B", "Trust"],
    setup: {
      title: "Source Trust Perception Study",
      description: "Measure how source labels and branding affect engagement and perceived credibility.",
      num_groups: 2,
      gaze_tracking_enabled: true,
      click_tracking_enabled: true,
      calibration_enabled: true,
      calibration_points: 9,
    },
    conditionNotes: ["Group 1 sees full source labels", "Group 2 sees reduced or neutralized source cues"],
    suggestedFlow: [
      "Use 4 article cards from mixed-familiarity outlets.",
      "Add source recall and trust questions after the second and fourth post.",
      "Review source-sensitive engagement differences in analytics.",
    ],
  },
  {
    id: "health-misinformation",
    source: "built_in",
    name: "Health Misinformation Response",
    category: "Health",
    summary: "Capture attention, sharing intent, and comment sentiment around health-information claims.",
    groups: 3,
    postSlots: 6,
    questionBlocks: 10,
    tags: ["Health", "Comments", "Tracking"],
    setup: {
      title: "Health Misinformation Response Study",
      description: "Track participant reactions to health claims with varied headline framing and social proof conditions.",
      num_groups: 3,
      gaze_tracking_enabled: true,
      click_tracking_enabled: true,
      calibration_enabled: true,
      calibration_points: 9,
    },
    conditionNotes: [
      "Group 1 sees neutral headlines",
      "Group 2 sees emotionally amplified headlines",
      "Group 3 sees amplified headlines with comments enabled",
    ],
    suggestedFlow: [
      "Load 6 article cards split across accurate and misleading health claims.",
      "Ask for sharing intent and concern rating after each post.",
      "Use analytics to compare comments, clicks, and completion quality by condition.",
    ],
  },
  {
    id: "sponsored-post-recall",
    source: "built_in",
    name: "Sponsored Post Recall",
    category: "Ads",
    summary: "Study recognition and recall for sponsored social posts with minimal setup time.",
    groups: 1,
    postSlots: 3,
    questionBlocks: 5,
    tags: ["Ads", "Recall"],
    setup: {
      title: "Sponsored Post Recall Study",
      description: "Measure recall, click behaviour, and participant sentiment for sponsored content in-feed.",
      num_groups: 1,
      gaze_tracking_enabled: false,
      click_tracking_enabled: true,
      calibration_enabled: false,
      calibration_points: 0,
    },
    conditionNotes: ["Single-group baseline with sponsored labels left visible"],
    suggestedFlow: [
      "Insert 3 ad-like posts with consistent brand cues.",
      "Add recall and purchase-intent question blocks after the final post.",
      "Export post-level click and comment totals for reporting.",
    ],
  },
];

export function loadSavedTemplates(): TemplateDefinition[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as TemplateDefinition[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function persistTemplate(template: TemplateDefinition) {
  if (typeof window === "undefined") return;
  const current = loadSavedTemplates().filter((item) => item.id !== template.id);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify([template, ...current]));
}

export function buildTemplateFromSurvey(input: {
  name: string;
  survey: {
    id: number;
    title: string;
    description?: string | null;
    num_groups: number;
    gaze_tracking_enabled?: boolean;
    gaze_interval_ms?: number;
    click_tracking_enabled?: boolean;
    calibration_enabled?: boolean;
    calibration_points?: number;
  };
  posts: Array<{
    original_url: string;
    display_title: string | null;
    display_image_url: string | null;
    display_likes: number;
    display_comments_count: number;
    display_shares: number;
    show_likes: boolean;
    show_comments: boolean;
    show_shares: boolean;
    visible_to_groups: number[] | null;
    group_overrides?: Record<string, { display_likes: number; display_comments_count: number; display_shares: number }> | null;
    comments: Array<{ author_name: string; text: string }>;
  }>;
}): TemplateDefinition {
  const { survey, posts, name } = input;
  return {
    id: `saved-${Date.now()}`,
    source: "saved",
    name,
    category: "Saved",
    summary: `Reusable copy of "${survey.title}" with ${posts.length} configured post cards.`,
    groups: survey.num_groups,
    postSlots: posts.length,
    questionBlocks: 0,
    tags: ["Saved", posts.length > 0 ? "Posts" : "Setup"],
    setup: {
      title: survey.title,
      description: survey.description || "",
      num_groups: survey.num_groups,
      gaze_tracking_enabled: survey.gaze_tracking_enabled ?? true,
      gaze_interval_ms: survey.gaze_interval_ms ?? 1000,
      click_tracking_enabled: survey.click_tracking_enabled ?? true,
      calibration_enabled: survey.calibration_enabled ?? true,
      calibration_points: survey.calibration_points ?? 9,
    },
    conditionNotes: [
      survey.num_groups > 1
        ? `Carries forward the ${survey.num_groups}-group experiment structure from the source survey.`
        : "Carries forward the single-group baseline from the source survey.",
    ],
    suggestedFlow: [
      "Review the imported posts before publishing the cloned study.",
      "Update article URLs or engagement baselines where needed.",
      "Use analytics to compare the cloned setup against the original survey.",
    ],
    posts: posts.map((post) => ({
      original_url: post.original_url,
      display_title: post.display_title,
      display_image_url: post.display_image_url,
      display_likes: post.display_likes,
      display_comments_count: post.display_comments_count,
      display_shares: post.display_shares,
      show_likes: post.show_likes,
      show_comments: post.show_comments,
      show_shares: post.show_shares,
      visible_to_groups: post.visible_to_groups,
      group_overrides: post.group_overrides || null,
      comments: post.comments.map((comment) => ({
        author_name: comment.author_name,
        text: comment.text,
      })),
    })),
  };
}