"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ChartIcon, CheckCircleIcon, SearchIcon, TemplateIcon, UsersIcon } from "@/components/icons";
import { defaultTemplateLibrary, loadSavedTemplates, type TemplateDefinition } from "@/lib/template-library";

const baseCategories = ["All", "News", "Trust", "Health", "Ads", "Saved"];

export default function TemplatesPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [savedTemplates, setSavedTemplates] = useState<TemplateDefinition[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState(defaultTemplateLibrary[0]?.id ?? "");
  const [creatingTemplate, setCreatingTemplate] = useState<string | null>(null);

  useEffect(() => {
    setSavedTemplates(loadSavedTemplates());
  }, []);

  const templateLibrary = useMemo(
    () => [...savedTemplates, ...defaultTemplateLibrary],
    [savedTemplates],
  );

  const categories = useMemo(() => {
    const dynamic = new Set(baseCategories);
    templateLibrary.forEach((template) => dynamic.add(template.category));
    return Array.from(dynamic);
  }, [templateLibrary]);

  const filteredTemplates = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return templateLibrary.filter((template) => {
      if (activeCategory !== "All" && template.category !== activeCategory) return false;
      if (!needle) return true;
      return (
        template.name.toLowerCase().includes(needle) ||
        template.summary.toLowerCase().includes(needle) ||
        template.tags.some((tag) => tag.toLowerCase().includes(needle))
      );
    });
  }, [activeCategory, search, templateLibrary]);

  const selectedTemplate =
    filteredTemplates.find((template) => template.id === selectedTemplateId) ??
    filteredTemplates[0] ??
    templateLibrary[0];

  useEffect(() => {
    if (selectedTemplate && selectedTemplate.id !== selectedTemplateId) {
      setSelectedTemplateId(selectedTemplate.id);
    }
  }, [selectedTemplate, selectedTemplateId]);

  async function createFromTemplate(template: TemplateDefinition) {
    setCreatingTemplate(template.id);
    try {
      const survey = await api.createSurvey(template.setup);

      if (template.posts?.length) {
        for (const [index, post] of template.posts.entries()) {
          const createdPost = await api.createPost(survey.id, {
            original_url: post.original_url,
            order: index + 1,
          });

          await api.updatePost(survey.id, createdPost.id, {
            display_title: post.display_title,
            display_image_url: post.display_image_url,
            display_likes: post.display_likes,
            display_comments_count: post.display_comments_count,
            display_shares: post.display_shares,
            show_likes: post.show_likes,
            show_comments: post.show_comments,
            show_shares: post.show_shares,
            visible_to_groups: post.visible_to_groups,
            group_overrides: post.group_overrides,
            order: index + 1,
          });

          for (const comment of post.comments) {
            await api.addComment(survey.id, createdPost.id, comment);
          }
        }
      }

      router.push(`/admin/surveys/${survey.id}?unsaved=1`);
    } finally {
      setCreatingTemplate(null);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-118px)] flex-col">
      <section className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 className="page-title">Templates</h1>
          <p className="page-subtitle">Reuse proven survey structures, condition logic, and question flows.</p>
        </div>
        <div className="flex w-full max-w-[420px] items-center gap-3">
          <div className="relative flex-1">
            <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search templates..."
              className="field-input bg-white py-2 pl-11 pr-4"
            />
          </div>
          <button
            type="button"
            onClick={() => router.push("/admin/surveys/new")}
            className="secondary-button min-w-[152px]"
          >
            Create Blank Survey
          </button>
        </div>
      </section>

      <section className="mt-5 grid flex-1 gap-5 xl:grid-cols-[220px_minmax(0,1fr)_320px]">
        <aside className="surface-panel-soft px-5 py-5">
          <p className="section-kicker">Categories</p>
          <div className="mt-4 space-y-1.5">
            {categories.map((category) => (
              <button
                key={category}
                type="button"
                onClick={() => setActiveCategory(category)}
                className={`flex w-full items-center justify-between rounded-[16px] px-3 py-2.5 text-left text-[13px] font-medium transition ${
                  activeCategory === category ? "bg-white text-black shadow-sm" : "text-slate-500 hover:bg-white/70 hover:text-black"
                }`}
              >
                <span>{category}</span>
                <span className="text-[11px] uppercase tracking-[0.2em] text-slate-400">
                  {category === "All"
                    ? templateLibrary.length
                    : templateLibrary.filter((template) => template.category === category).length}
                </span>
              </button>
            ))}
          </div>

          <div className="mt-8">
            <p className="section-kicker">Included</p>
            <div className="mt-4 space-y-3">
              {["A/B-ready structures", "Tracking defaults", "Suggested question flow", "Reusable post setup"].map((item) => (
                <div key={item} className="flex items-start gap-3">
                  <CheckCircleIcon className="mt-0.5 h-4 w-4 text-black" />
                  <p className="text-[14px] leading-7 text-slate-500">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <div className="space-y-4">
          {filteredTemplates.map((template) => {
            const selected = selectedTemplate?.id === template.id;
            return (
              <button
                key={template.id}
                type="button"
                onClick={() => setSelectedTemplateId(template.id)}
                className={`surface-panel flex w-full flex-col gap-4 p-5 text-left transition ${
                  selected ? "border-black/15 shadow-[0_24px_60px_rgba(17,24,39,0.08)]" : "hover:-translate-y-0.5"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="section-kicker">{template.category}</p>
                      {template.source === "saved" && (
                        <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                          Saved
                        </span>
                      )}
                    </div>
                    <h2 className="mt-3 text-[20px] font-semibold tracking-[-0.04em] text-black">{template.name}</h2>
                    <p className="mt-2 text-[14px] leading-7 text-slate-500">{template.summary}</p>
                  </div>
                  <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-stone-100 text-slate-500">
                    <TemplateIcon className="h-4 w-4" />
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-[16px] border bg-stone-50 px-4 py-3">
                    <p className="section-kicker">Groups</p>
                    <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{template.groups}</p>
                  </div>
                  <div className="rounded-[16px] border bg-stone-50 px-4 py-3">
                    <p className="section-kicker">Post slots</p>
                    <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{template.postSlots}</p>
                  </div>
                  <div className="rounded-[16px] border bg-stone-50 px-4 py-3">
                    <p className="section-kicker">Questions</p>
                    <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{template.questionBlocks}</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {template.tags.map((tag) => (
                    <span key={tag} className="rounded-full bg-stone-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      {tag}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}

          {filteredTemplates.length === 0 && (
            <div className="surface-panel px-8 py-12 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-[18px] bg-stone-100 text-slate-500">
                <TemplateIcon className="h-5 w-5" />
              </div>
              <h2 className="mt-5 text-[22px] font-semibold tracking-[-0.04em] text-black">No matching templates</h2>
              <p className="mx-auto mt-2 max-w-xl text-[14px] leading-7 text-slate-500">
                Refine your search or switch categories to explore more reusable survey structures.
              </p>
            </div>
          )}
        </div>

        <aside className="space-y-5">
          {selectedTemplate && (
            <>
              <div className="surface-panel px-6 py-6">
                <p className="section-kicker">Template preview</p>
                <h2 className="mt-3 text-[22px] font-semibold tracking-[-0.04em] text-black">{selectedTemplate.name}</h2>
                <p className="mt-2 text-[14px] leading-7 text-slate-500">{selectedTemplate.summary}</p>

                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-[16px] border bg-stone-50 px-4 py-3">
                    <p className="section-kicker">Tracking</p>
                    <p className="mt-2 text-[14px] leading-7 text-slate-600">
                      {selectedTemplate.setup.click_tracking_enabled ? "Click" : "No click"} ·{" "}
                      {selectedTemplate.setup.gaze_tracking_enabled ? "Gaze" : "No gaze"} ·{" "}
                      {selectedTemplate.setup.calibration_enabled ? "Calibration" : "No calibration"}
                    </p>
                  </div>
                  <div className="rounded-[16px] border bg-stone-50 px-4 py-3">
                    <p className="section-kicker">Structure</p>
                    <p className="mt-2 text-[14px] leading-7 text-slate-600">
                      {selectedTemplate.groups} groups · {selectedTemplate.postSlots} posts · {selectedTemplate.questionBlocks} question blocks
                    </p>
                  </div>
                </div>

                <div className="mt-6 space-y-4">
                  <div>
                    <p className="section-kicker">Condition logic</p>
                    <div className="mt-3 space-y-3">
                      {selectedTemplate.conditionNotes.map((note) => (
                        <div key={note} className="flex items-start gap-3">
                          <UsersIcon className="mt-0.5 h-4 w-4 text-slate-500" />
                          <p className="text-[14px] leading-7 text-slate-500">{note}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="section-kicker">Suggested flow</p>
                    <div className="mt-3 space-y-3">
                      {selectedTemplate.suggestedFlow.map((step) => (
                        <div key={step} className="flex items-start gap-3">
                          <ChartIcon className="mt-0.5 h-4 w-4 text-slate-500" />
                          <p className="text-[14px] leading-7 text-slate-500">{step}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => createFromTemplate(selectedTemplate)}
                  disabled={creatingTemplate === selectedTemplate.id}
                  className="primary-button mt-6 w-full py-3"
                >
                  {creatingTemplate === selectedTemplate.id ? "Creating..." : "Use Template"}
                </button>
              </div>

              <div className="surface-panel-soft px-6 py-6">
                <p className="section-kicker">Why this helps</p>
                <p className="mt-3 text-[14px] leading-7 text-slate-500">
                  Templates standardize your tracking defaults, group structure, and question rhythm before you start
                  inserting article URLs, which makes cross-study comparisons much cleaner.
                </p>
              </div>
            </>
          )}
        </aside>
      </section>
    </div>
  );
}