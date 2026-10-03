from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
WORK = ROOT/'build'
WORK.mkdir(parents=True,exist_ok=True)
text=(ROOT/'PACT_From_Instructions_to_Procedures.md').read_text()
paras=text.strip().split('\n\n')

def esc(s):
    return ''.join({'&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}','\\':r'\textbackslash{}'}.get(c,c) for c in s)

def prose(s):
    tokens=[]
    def token(value):
        tokens.append(value);return f'@@TOKEN{len(tokens)-1}@@'
    s=re.sub(r'https://[^\s]+',lambda m:token(r'\url{'+m[0]+'}'),s)
    s=re.sub(r'(test_local_selection_keeps_terminal_official_default_safety_net|perf_counter_ns|trace_enabled=False|manual_guarded)',lambda m:token(r'{\small\urlstyle{tt}\nolinkurl{'+m[0]+'}}'),s)
    s=re.sub(r'(?<![\w/])(experiment\.[\w.-]+|(?:agent|text)\.[\w.-]+|domain\.noun\.verb)',lambda m:token(r'{\small\urlstyle{tt}\nolinkurl{'+m[0]+'}}'),s)
    s=re.sub(r'(?<![\w.])\[(\d+)\]',lambda m:token(r'\cite{r'+m[1]+'}'),s)
    s=esc(s)
    for i,t in enumerate(tokens):s=s.replace(f'@@TOKEN{i}@@',t)
    return s

preamble=r'''\documentclass[10pt,twocolumn,a4paper]{article}
\usepackage[margin=0.72in,top=0.78in,bottom=0.75in,columnsep=0.25in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{mathptmx}
\usepackage{courier}
\usepackage{balance}
\usepackage{placeins}
\usepackage{amsmath}
\usepackage{microtype}
\usepackage{booktabs,array,tabularx}
\usepackage{graphicx}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning}
\usepackage[font=small,labelfont=bf,labelsep=period]{caption}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\hypersetup{pdftitle={From Agent Instructions to Executable Procedures: The PACT Architecture},pdfauthor={Noah Dylan Pelegrini},pdfsubject={Procedural Agent Composition and Traceability}}
\urlstyle{same}
\titleformat{\section}{\normalsize\bfseries\raggedright\hyphenpenalty=10000}{\thesection}{0.6em}{}
\titleformat{\subsection}{\normalsize\bfseries\raggedright\hyphenpenalty=10000}{\thesubsection}{0.6em}{}
\titlespacing*{\section}{0pt}{2.2ex plus .3ex minus .2ex}{1.1ex plus .2ex}
\titlespacing*{\subsection}{0pt}{1.8ex plus .2ex minus .2ex}{.8ex plus .1ex}
\setlength{\parindent}{1em}
\setlength{\parskip}{0pt}
\setlength{\headheight}{12pt}
\setlength{\textfloatsep}{12pt plus 2pt minus 2pt}
\setlength{\dbltextfloatsep}{12pt plus 2pt minus 2pt}
\setlength{\floatsep}{10pt plus 2pt minus 2pt}
\renewcommand{\topfraction}{.9}
\renewcommand{\dbltopfraction}{.9}
\renewcommand{\textfraction}{.07}
\renewcommand{\floatpagefraction}{.8}
\setcounter{topnumber}{3}
\setcounter{dbltopnumber}{3}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\footnotesize PACT: Procedural Agent Composition and Traceability}
\fancyhead[R]{\footnotesize N. D. Pelegrini}
\fancyfoot[C]{\footnotesize\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\raggedbottom
\emergencystretch=1em
\begin{document}
\twocolumn[{
\centering
{\LARGE\bfseries From Agent Instructions to Executable Procedures:\\[3pt] The PACT Architecture\par}
\vspace{10pt}
{\large Noah Dylan Pelegrini\par}
\vspace{3pt}
Independent Researcher\\
\href{mailto:contact@11adyy.dev}{contact@11adyy.dev}\\
\url{https://github.com/11adyy/pact-research}
\vspace{12pt}
\begin{minipage}{0.94\textwidth}
\small
\noindent\textbf{Abstract.} ABSTRACT_TEXT
\end{minipage}
\vspace{16pt}
}]
\thispagestyle{plain}
'''

fig1=r'''\begin{figure}[t]
\centering
\begin{tikzpicture}[font=\footnotesize,>=Stealth,
box/.style={draw,thin,align=center,inner sep=5pt,text width=7.35cm},
half/.style={draw,thin,align=center,inner sep=4pt,text width=3.30cm}]
\node[box] (agent) {\textbf{Agent layer}\\Goals, policies, procedure selection};
\node[half,below=6mm of agent.south west,anchor=north west] (skill) {\textbf{Skills and capabilities}\\Operation interfaces\\and dependencies};
\node[half,right=4mm of skill] (state) {\textbf{Execution state}\\Inputs, intermediate values,\\outputs, trace};
\node[box,below=28mm of agent] (binding) {\textbf{Bindings and implementations}\\Models, APIs, and deterministic functions};
\draw[->] (agent.south -| skill.north)--(skill.north);
\draw[->] (agent.south -| state.north)--(state.north);
\draw[->] (skill)--(state);
\draw[->] (skill.south)--(binding.north -| skill.south);
\draw[->] (state.south)--(binding.north -| state.south);
\end{tikzpicture}
\caption{The procedural boundary. Skills and capability interfaces describe the task; named state exposes its data; bindings connect the description to execution. The agent retains goal and policy responsibilities.}
\label{fig:model}
\end{figure}
'''

fig2=r'''\begin{figure*}[t]
\centering
\begin{tikzpicture}[font=\small,>=Stealth,
wide/.style={draw,thin,align=center,inner sep=5pt,text width=15.1cm},
part/.style={draw,thin,align=center,inner sep=5pt,text width=4.6cm}]
\node[wide] (entry) {\textbf{Developer interfaces}\\CLI; HTTP API and SSE; SDK integrations; MCP server; native model adapters};
\node[wide,below=4mm of entry] (gateway) {\textbf{Skill gateway} --- discovery, ranking, governance};
\node[part,below=6mm of gateway] (policy) {\textbf{Policy engine}\\Safety gates, trust levels,\\confirmation requirements};
\node[part,left=4mm of policy] (scheduler) {\textbf{DAG scheduler}\\Topological ordering;\\sequential or parallel steps};
\node[part,right=4mm of policy] (state) {\textbf{Structured state}\\Frame, Working, Output, Trace};
\node[wide,below=6mm of policy] (resolver) {\textbf{Binding resolver} --- protocol routing, defaults and overrides, fallback, conformance};
\node[wide,below=4mm of resolver] (services) {\textbf{Execution targets}\\PythonCall / OpenAPI / MCP / OpenRPC\\Local deterministic functions; external APIs; in-process or subprocess services};
\draw[->] (entry)--(gateway);
\draw[->] (gateway.south -| scheduler.north)--(scheduler.north);
\draw[->] (gateway)--(policy);
\draw[->] (gateway.south -| state.north)--(state.north);
\draw[->] (scheduler.south)--(resolver.north -| scheduler.south);
\draw[->] (policy)--(resolver);
\draw[->] (state.south)--(resolver.north -| state.south);
\draw[->] (resolver)--(services);
\end{tikzpicture}
\caption{Reference runtime organization. The integration surface converges on a gateway and execution substrate, while implementation resolution isolates service-specific transports from procedural definitions.}
\label{fig:runtime}
\end{figure*}
'''

table1=r'''\begin{table*}[t]
\centering
\caption{Qualitative comparison of representative architectural patterns, retained from the source account. Entries describe patterns rather than exhaustive framework capabilities.}
\label{tab:comparison}
\small
\begin{tabular}{@{}p{7cm}lll@{}}
\toprule
Architectural concern & PACT & LangChain-style & ReAct-style\\
\midrule
Declarative procedures & Explicit & Partial & Absent\\
Late implementation binding & Explicit & Partial & Absent\\
Structured execution state & Explicit & Limited & Absent\\
Reusable capability units & Explicit & Partial & Absent\\
Step-level observability & Explicit & Partial & Limited\\
\bottomrule
\end{tabular}
\end{table*}
'''

table2=r'''\begin{table*}[t]
\centering
\caption{Operational observations from the source evaluation. Variability is reported as Jaccard distance; validity is qualitative. Neither measures semantic accuracy.}
\label{tab:results}
\small
\begin{tabular}{@{}p{7.4cm}ll@{}}
\toprule
Reported dimension & Single-call prompt & Structured procedure\\
\midrule
Mean decision latency & 4.79 s & 12.17 s\\
Mean text-processing latency & 2.93 s & 7.86 s\\
Intermediate execution trace & Not exposed & Step-level\\
Independent component reuse & Not exposed & Capability-level\\
Text-output variability & $\sim$0.12 & $\sim$0.17\\
Qualitative output validity & High & High\\
\bottomrule
\end{tabular}
\end{table*}
'''

extended_tables = {'TABLE_ARMS': '\\begin{table*}[t]\n\\centering\n\\caption{Extended-study execution arms. The primary comparator matches five service invocations and declared governance checks; the direct and transport arms are supplemental lower bounds.}\n\\label{tab:arms}\n\\small\n\\setlength{\\tabcolsep}{4pt}\n\\renewcommand{\\arraystretch}{1.12}\n\\begin{tabularx}{\\textwidth}{@{}p{3.3cm}X@{}}\n\\toprule\nArm & Execution configuration\\\\\n\\midrule\ndirect & Shared workload functions called directly\\\\\ntransport & Same functions through the native PythonCallInvoker and per-call threads\\\\\nmanual\\_guarded & Transport plus independent type/policy checks and the same integrity gate\\\\\npact & Full native runtime, contracts, scheduling, state mapping, binding resolution, and gates\\\\\npact\\_no\\_policy & Loader adapter removes safety metadata; runtime source unchanged\\\\\npact\\_no\\_validation & Bypass capability validation/enrichment; planning, response mapping and transport retained\\\\\npact\\_trace\\_off & Public trace\\_enabled=False; actual structured trace contents recorded\\\\\npact\\_static\\_binding & Freeze initial native resolver choices; remaining layers retained\\\\\n\\bottomrule\n\\end{tabularx}\n\\end{table*}', 'TABLE_HEALTHY_EXTENDED': '\\begin{table*}[t]\n\\centering\n\\caption{Healthy deterministic workloads: 100 distinct inputs per family, three repetitions. Success requires exact oracle agreement in every repetition. Latency is in milliseconds; the paired-difference interval uses case bootstrap resampling.}\n\\label{tab:healthy-extended}\n\\small\n\\setlength{\\tabcolsep}{4pt}\n\\renewcommand{\\arraystretch}{1.12}\n\\begin{tabularx}{\\textwidth}{@{}Xlllll@{}}\n\\toprule\nTask & PACT cases & PACT mean & Manual mean & Paired delta & 95\\% interval\\\\\n\\midrule\nsum & 100/100 & 12.081 & 0.586 & 11.494 & [11.366, 11.673]\\\\\nmax & 100/100 & 12.096 & 0.601 & 11.495 & [11.387, 11.609]\\\\\ndecision & 100/100 & 12.139 & 0.729 & 11.411 & [11.334, 11.486]\\\\\ntext & 100/100 & 12.250 & 0.611 & 11.639 & [11.387, 12.065]\\\\\n\\bottomrule\n\\end{tabularx}\n\\end{table*}', 'TABLE_ROBUST_EXTENDED': '\\begin{table*}[t]\n\\centering\n\\caption{Expected-behavior counts on 100 distinct inputs per scenario. Recovery requires exact output; containment requires failure without an effect. Terminal output is scored for rejection. The transport arm has no policy or deadline guard.}\n\\label{tab:faults-extended}\n\\small\n\\setlength{\\tabcolsep}{4pt}\n\\renewcommand{\\arraystretch}{1.12}\n\\begin{tabularx}{\\textwidth}{@{}Xlll@{}}\n\\toprule\nScenario & Transport & Manual guarded & PACT\\\\\n\\midrule\nservice exception & 100/100 & 100/100 & 100/100\\\\\nmissing output & 100/100 & 100/100 & 100/100\\\\\nwrong intermediate type & 0/100 & 100/100 & 100/100\\\\\nnull intermediate & 0/100 & 100/100 & 0/100\\\\\nnegative semantic result & 0/100 & 100/100 & 100/100\\\\\nplausible wrong result & 0/100 & 0/100 & 0/100\\\\\nterminal output type & 0/100 & 100/100 & 0/100\\\\\nlow trust & 0/100 & 100/100 & 100/100\\\\\nunconfirmed effect & 0/100 & 100/100 & 100/100\\\\\ncross tenant & 0/100 & 100/100 & 100/100\\\\\nmissing tenant & 0/100 & 100/100 & 100/100\\\\\nmissing target tenant & 0/100 & 100/100 & 0/100\\\\\ntransient recovered & 100/100 & 100/100 & 100/100\\\\\ntransient no retry & 100/100 & 100/100 & 100/100\\\\\nstep timeout & 0/100 & 100/100 & 100/100\\\\\nlate effect after timeout & 0/100 & 0/100 & 0/100\\\\\n\\bottomrule\n\\end{tabularx}\n\\end{table*}', 'TABLE_ABLATIONS_EXTENDED': '\\begin{table*}[t]\n\\centering\n\\caption{Selected ablation outcomes: expected behavior over 100 inputs. Other checks remain active when capability validation is bypassed; failure at a retained layer can therefore mask the ablated check.}\n\\label{tab:ablations-extended}\n\\small\n\\setlength{\\tabcolsep}{4pt}\n\\renewcommand{\\arraystretch}{1.12}\n\\begin{tabularx}{\\textwidth}{@{}Xlll@{}}\n\\toprule\nScenario & Full PACT & No safety metadata & No capability validation\\\\\n\\midrule\nlow trust & 100/100 & 0/100 & 100/100\\\\\nunconfirmed effect & 100/100 & 0/100 & 100/100\\\\\ncross tenant & 100/100 & 0/100 & 100/100\\\\\nmissing output & 100/100 & 100/100 & 100/100\\\\\nwrong intermediate type & 100/100 & 100/100 & 0/100\\\\\nnegative semantic result & 100/100 & 0/100 & 100/100\\\\\n\\bottomrule\n\\end{tabularx}\n\\end{table*}', 'TABLE_SCALING_EXTENDED': '\\begin{table*}[t]\n\\centering\n\\caption{Matched identity-chain microbenchmarks, 20 runs per length/delay/arm. All time columns are milliseconds; delays are artificial service delays. Paired differences compare native PACT with transport.}\n\\label{tab:scaling-extended}\n\\small\n\\setlength{\\tabcolsep}{4pt}\n\\renewcommand{\\arraystretch}{1.12}\n\\begin{tabularx}{\\textwidth}{@{}Xlllll@{}}\n\\toprule\nSteps & Delay/call & Transport mean & PACT mean & Paired delta & 95\\% interval\\\\\n\\midrule\n1 & 0 & 0.16 & 3.39 & 3.22 & [3.12, 3.33]\\\\\n2 & 0 & 0.29 & 5.54 & 5.24 & [5.10, 5.41]\\\\\n8 & 0 & 0.87 & 18.40 & 17.53 & [17.19, 17.86]\\\\\n16 & 0 & 1.63 & 34.09 & 32.47 & [31.79, 33.19]\\\\\n32 & 0 & 2.82 & 68.26 & 65.45 & [64.46, 66.53]\\\\\n1 & 1 & 1.26 & 4.57 & 3.31 & [3.17, 3.46]\\\\\n2 & 1 & 2.49 & 7.80 & 5.31 & [5.15, 5.47]\\\\\n8 & 1 & 9.83 & 27.16 & 17.33 & [17.03, 17.64]\\\\\n16 & 1 & 19.67 & 54.38 & 34.71 & [32.83, 37.71]\\\\\n32 & 1 & 39.39 & 103.78 & 64.39 & [62.91, 66.02]\\\\\n\\bottomrule\n\\end{tabularx}\n\\end{table*}', 'TABLE_FANOUT_EXTENDED': '\\begin{table*}[t]\n\\centering\n\\caption{Independent branches plus merge, 5 ms branch delay, 12 runs per configuration. Mean elapsed time is in milliseconds. Completion and declared call count succeed for both arms in every configuration.}\n\\label{tab:fanout-extended}\n\\small\n\\setlength{\\tabcolsep}{4pt}\n\\renewcommand{\\arraystretch}{1.12}\n\\begin{tabularx}{\\textwidth}{@{}Xllllp{3.1cm}@{}}\n\\toprule\nBranches & Transport, 1 worker & Transport, 4 workers & PACT, 1 worker & PACT, 4 workers & PACT success\\\\\n\\midrule\n1 & 5.63 & 5.63 & 14.79 & 11.03 & 12/12 at both settings\\\\\n2 & 10.94 & 5.78 & 18.23 & 13.36 & 12/12 at both settings\\\\\n4 & 21.39 & 6.36 & 33.01 & 18.10 & 12/12 at both settings\\\\\n8 & 42.79 & 11.96 & 63.39 & 32.02 & 12/12 at both settings\\\\\n\\bottomrule\n\\end{tabularx}\n\\end{table*}', 'TABLE_LLM_REPORTED': '\\begin{table*}[t]\n\\centering\n\\caption{Additional author-reported LLM aggregates (unverified). No original trial records accompany these values; they are not included in the independently measured execution count.}\n\\label{tab:llm-reported}\n\\small\n\\setlength{\\tabcolsep}{4pt}\n\\renewcommand{\\arraystretch}{1.12}\n\\begin{tabularx}{\\textwidth}{@{}Xlll@{}}\n\\toprule\nReported metric & Single call & Manual, 3 calls & PACT, 3 calls\\\\\n\\midrule\nExact-output rate & 86\\% & 92\\% & 92\\%\\\\\nInputs correct in all three repetitions & 78/100 & 87/100 & 88/100\\\\\nMean elapsed time & 1.80 s & 4.90 s & 4.92 s\\\\\nMean total tokens per execution & 678 & 1,378 & 1,378\\\\\n\\bottomrule\n\\end{tabularx}\n\\end{table*}'}

abstract=paras[3]
assert paras[2]=='## Abstract'
output=[preamble.replace('ABSTRACT_TEXT',prose(abstract))]
inrefs=False
for para in paras[4:]:
    if para=='## References':
        output.append(r'\begin{thebibliography}{8}'+'\n'+r'\small'+'\n');inrefs=True
    elif inrefs:
        m=re.match(r'\[(\d+)\]\s*(.*)',para,re.S)
        output.append(r'\bibitem{r'+m[1]+'} '+prose(m[2])+'\n')
    elif para.startswith('### '):
        name=re.sub(r'^\d+\.\d+\s+','',para[4:])
        output.append(r'\subsection{'+esc(name)+'}\n')
    elif para.startswith('## '):
        name=re.sub(r'^\d+\.\s+','',para[3:])
        if name=='Deployment Trade-offs and Remaining Work':output.append(r'\FloatBarrier'+'\n')
        if name=='Conclusion':output.append(r'\balance\thispagestyle{fancy}'+'\n')
        output.append(r'\section{'+esc(name)+'}\n')
    elif para.startswith('$$'):
        math=para[2:-2].replace('->',r'\rightarrow').replace('implementation',r'\mathrm{implementation}')
        output.append(r'\begin{equation}'+math+r'\end{equation}'+'\n')
    elif para=='[[FIGURE_MODEL]]':output.append(fig1)
    elif para=='[[FIGURE_RUNTIME]]':output.append(fig2)
    elif para=='[[TABLE_COMPARISON]]':output.append(table1)
    elif para=='[[TABLE_RESULTS]]':output.append(table2)
    elif para.startswith('[[') and para[2:-2] in extended_tables:output.append(extended_tables[para[2:-2]])
    else:output.append(prose(para)+'\n\n')
output.extend([r'\end{thebibliography}',r'\end{document}'])
(WORK/'PACT_From_Instructions_to_Procedures.tex').write_text('\n'.join(output))
print(WORK/'PACT_From_Instructions_to_Procedures.tex')
