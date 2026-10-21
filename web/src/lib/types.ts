// Data contract with dpcn/export_web.py -- every file under public/data/.

export type InstKey = "IISERB" | "IISERM" | "IISERTVM";
export type Scope = InstKey | "ALL";

export interface InstituteMeta {
  key: InstKey; name: string; short: string; city: string; color: string;
  openalex: string; ror: string; lat: number; lon: number;
}

export interface Meta {
  generated: string; group: number;
  institutes: InstituteMeta[];
  counts: { faculty_listed: number; faculty_matched: number; papers: number; rows: number;
            citations: number; citation_edges: number; coauthor_pairs: number; partners: number; linked_institutes: number };
  coverage: { faculty_match: number; doi: number; quartile: number; affiliated_rows: number };
  hyperauthor_cap: number;
  openalex_spend_note: string;
  downloads: { label: string; file: string; url: string; rows: number; desc: string }[];
  links: { repo: string; dashboard: string; drive: string };
}

export interface PaperCard {
  work_id: string; title: string; source_name?: string; journal?: string; year: number;
  cited_by_count?: number; citations?: number; doi?: string | null; n_authors?: number;
  hyperauthored?: boolean; inst?: InstKey[]; score?: number; internal_in?: number;
}

export interface InstituteStats {
  papers: number; citations: number; citations_excl_hyper: number; hyperauthored_papers: number;
  mean_citations: number; median_citations: number; median_fwci: number | null; mean_fwci: number | null;
  top10pct_share: number; oa_share: number; intl_share: number;
  journal_papers: number; conference_papers: number; quartile_coverage: number;
  quartiles: Record<"Q1" | "Q2" | "Q3" | "Q4", number>; q1_share: number;
  q_by_year: Record<string, Partial<Record<"Q1" | "Q2" | "Q3" | "Q4", number>>>;
  core: Record<string, number>;
  by_year: Record<string, number>; cites_by_year: Record<string, number>;
  cagr: number | null;
  trend_nb: { annual_growth: number; growth_p: number; covid_effect: number; covid_p: number };
  mann_kendall: { trend: string; p: number; tau: number; sen_slope: number };
  gini_citations: number; lorenz: [number, number][];
  top_journals: { source_name: string; papers: number; citations: number; quartile: string | null }[];
  top_cited: PaperCard[]; top_cited_excl_hyper: PaperCard[];
  fields: Record<string, number>;
  subfields: { domain: string; field: string; subfield: string; n: number }[];
}

export interface Institutes {
  institutes: Record<Scope, InstituteStats>;
  tests: {
    h_index_kruskal: { H: number; p: number; dunn_holm: Record<string, number> };
    h_window_kruskal: { H: number; p: number };
    quartile_chi2: { chi2: number; p: number; dof: number; cramers_v: number };
    fwci_kruskal: { H: number; p: number };
    teamsize_citation_spearman: { rho: number; p: number };
  };
  h_hist: Record<InstKey, number[]>;
  departments: Department[];
}

export interface Department {
  institution: InstKey; department: string; faculty: number; papers: number; papers_per_faculty: number;
  citations: number; q1_share: number | null; median_h_career: number | null; median_h_window: number;
}

export interface Faculty {
  key: string; name: string; institution: InstKey; department: string; designation: string;
  openalex_ids: string; match_confidence: string;
  papers: number; papers_affiliated: number; citations: number; citations_affiliated: number;
  h_index_window: number; h_index_career: number | null; i10_career: number | null; works_career: number | null;
  q1_share: number | null; top_journal: string | null; first_author_share: number | null;
  median_fwci: number | null; hyperauthored_papers: number; field: string | null;
  first_year_at_inst: number | null; by_year: Record<string, number>;
  degree?: number; strength?: number; betweenness?: number; eigenvector?: number;
  clustering?: number; core?: number; community?: number;
  coauthors?: { name: string; inst: string | null; papers: number }[];
}

export interface GraphNodeC {
  id: string; x: number; y: number; pr: number; inst: InstKey; multi: boolean; year: number;
  t: string; j: string; c: number; indeg: number; f: string | null; h: boolean; doi: string | null;
}
export interface CitationGraph { nodes: GraphNodeC[]; edges: [string, string][] }

export interface CitationStats {
  nodes: number; edges: number; density: number; isolated: number; wcc_count: number; giant_wcc: number;
  giant_wcc_share: number; reciprocity: number; mean_internal_in: number;
  pagerank_top: PaperCard[]; pagerank_top_excl_hyper: PaperCard[]; hits_authority_top: PaperCard[];
  indegree_dist: Record<string, number>;
  powerlaw: { alpha: number; xmin: number; vs_lognormal_R: number; vs_lognormal_p: number;
              vs_exponential_R: number; vs_exponential_p: number };
  flow_matrix: Record<InstKey, Record<InstKey, number>>; self_citation_share: number;
  lag_hist: Record<string, number>; median_lag: number | null;
  scope_counts: Record<string, number>;
}

export interface GraphNodeA {
  id: string; x: number; y: number; name: string; inst: InstKey; dept: string; degree: number;
  strength: number; betweenness: number; eigenvector: number; clustering: number; core: number; community: number;
}
export interface CoauthorGraph { nodes: GraphNodeA[]; edges: [string, string, number, number][] }

export interface Ranked { name: string; inst: InstKey; dept: string; value: number }
export interface CoauthorStats {
  nodes: number; connected: number; edges: number; isolates: number; density: number; mean_degree: number;
  components: number; giant_share: number; avg_clustering: number; transitivity: number; max_kcore: number;
  leiden_communities: number; leiden_modularity: number; louvain_communities: number; louvain_modularity: number;
  nmi_department: number; ari_department: number; nmi_institute: number;
  assortativity_department: number; assortativity_institute: number; degree_assortativity: number;
  cross_institute_edges: number;
  cross_institute_pairs: { a: string; ia: InstKey; b: string; ib: InstKey; w: number }[];
  top_degree: Ranked[]; top_strength: Ranked[]; top_betweenness: Ranked[]; top_eigenvector: Ranked[];
  bridges: { name: string; inst: InstKey; dept: string; other_depts: number; other_insts: number; betweenness: number }[];
  communities: { community: number; size: number; purity: number; top_groups: [string, number][]; insts: Record<string, number> }[];
  rich_club: Record<string, number>; degree_hist: Record<string, number>;
  small_world: { giant_nodes: number; C: number; L: number; C_null: number; L_null: number; sigma: number; sigma_p05?: number; sigma_p95?: number };
  with_hyperauthored: { edges: number; mean_degree: number };
  temporal: { year: number; active_faculty: number; edges: number; mean_degree: number; giant_share: number;
              modularity: number; cross_inst_edges: number }[];
  link_prediction: { split_year: number; candidates: number; positives: number; auc: Record<string, number | null>;
                     top_predictions: { a: string; b: string; score: number; realised: boolean }[] };
}

export interface Partner {
  partner_inst: string; partner_cluster: string; shared_papers: number; citations_in: number;
  citations_out: number; topic_jaccard: number | null; subfield_overlap: number | null;
  lat: number | null; lon: number | null;
}
export interface ConnectionStats {
  partners: number; citing_institutes: number; citations_in: number; citations_out: number;
  impact_ratio: number | null;
  top_citing: { partner_inst: string; partner_cluster: string; citations_in: number }[];
  top_partners: Partner[];
  by_cluster: Record<string, number>;
  in_by_year: Record<string, number>; out_by_year: Record<string, number>;
}
export type Connections = Record<InstKey, ConnectionStats>;

export interface SearchItem { k: "f" | "p" | "j"; id: string; label: string; sub: string; inst?: InstKey }
