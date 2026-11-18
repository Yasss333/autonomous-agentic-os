import { useRef, useState } from 'react'
import { ArrowArcLeftIcon, ArrowRightIcon, ArrowUpRightIcon, BuildingsIcon, ChartBarIcon, CheckIcon, ClockIcon, CubeIcon, GitBranchIcon, ListIcon, MinusIcon, PackageIcon, PlusIcon, ReceiptIcon, ShieldCheckIcon, SparkleIcon, UserCircleIcon, CheckSquareIcon } from '@phosphor-icons/react'
import './landing.css'

const examples = [
  {
    label: 'Follow up with idle leads',
    Icon: UserCircleIcon,
    prompt: 'Find open leads with no activity for seven days and create a follow-up task for each.',
    result: 'Three open leads matched the seven-day rule. The tool is ready to review before activation.',
    output: '3 matching leads · Follow-up tasks proposed',
    checks: ['Seven-day cutoff', 'Closed leads excluded', 'Duplicate tasks prevented'],
  },
  {
    label: 'Review the sales pipeline',
    Icon: ChartBarIcon,
    prompt: 'Group open leads by stage and show the total deal value in each stage.',
    result: 'The draft pipeline groups open leads by stage and sums their deal values.',
    output: 'Pipeline view · Grouped by stage',
    checks: ['Stage grouping', 'Deal value totals', 'Closed leads excluded'],
  },
  {
    label: 'Track team expenses',
    Icon: ReceiptIcon,
    prompt: 'Show pending expenses by category and put the largest claims first.',
    result: 'The draft expense view shows the pending claims, grouped for review.',
    output: 'Expense view · Sorted by amount',
    checks: ['Pending status filter', 'Category grouping', 'Descending amount sort'],
  },
  {
    label: 'Flag inventory to reorder',
    Icon: PackageIcon,
    prompt: 'Show items below their reorder threshold and sort by the biggest shortage first.',
    result: 'Two items are below their reorder threshold in the sample inventory.',
    output: '2 items flagged · Reorder view drafted',
    checks: ['Reorder threshold applied', 'Shortage sort applied', 'Item details preserved'],
  },
]

const capabilities = [
  [UserCircleIcon, 'Leads', 'Find the right records'],
  [BuildingsIcon, 'Companies', 'See account relationships'],
  [ClockIcon, 'Activity', 'Use contact history'],
  [CheckSquareIcon, 'Tasks', 'Propose follow-up work'],
  [SparkleIcon, 'Build Studio', 'Draft dashboard views'],
  [GitBranchIcon, 'Tool versions', 'Review and activate'],
]

function Wordmark() {
  return <a className="os-wordmark" href="/"><CubeIcon aria-hidden="true" className="os-mark" weight="duotone" />Agentic OS</a>
}

export function Landing() {
  const [selected, setSelected] = useState(0)
  const [showChecks, setShowChecks] = useState(false)
  const menu = useRef(null)
  const example = examples[selected]

  function selectExample(index) {
    setSelected(index)
    setShowChecks(false)
  }

  return (
    <div className="os-page">
      <a className="os-announcement" href="#demo"><strong>Interactive preview</strong><span>Explore a sample workflow <ArrowRightIcon aria-hidden="true" /></span></a>
      <div className="os-nav-wrap">
        <nav className="os-nav" aria-label="Main navigation">
          <Wordmark />
          <div className="os-nav-links">
            <a href="#workflow">Workflow</a><a href="#prompts">Use cases</a><a href="#controls">Safety</a>
          </div>
          <div className="os-actions">
            <a className="os-button os-outline" href="/login">Sign in</a>
            <a className="os-button os-desktop" href="#demo">Explore demo</a>
            <details className="os-menu" ref={menu}>
              <summary aria-label="Open navigation"><ListIcon aria-hidden="true" /></summary>
              <div onClick={() => { menu.current.open = false }}>
                <a href="#demo">Explore demo</a><a href="#workflow">Workflow</a>
                <a href="#prompts">Use cases</a><a href="#controls">Safety</a><a href="#faq">FAQ</a>
              </div>
            </details>
          </div>
        </nav>
      </div>
      <main>
        <header className="os-hero os-wash">
          <h1>Build CRM automations<br />with Agentic OS</h1>
          <p>Describe the workflow you need. Agentic OS builds and tests the tool, then shows you the results before you activate it.</p>
          <a className="os-button os-primary" href="#demo">Explore the demo <ArrowUpRightIcon aria-hidden="true" /></a>
        </header>

        <section className="os-demo-band" id="demo">
          <div className="os-wrap os-centered">
            <h2>Watch a request become a tool</h2>
            <p>Pick a sample workflow to see what the agent would build.</p>
            <div className="os-picker" aria-label="Sample workflows">
              {examples.map(({ Icon, label }, index) => (
                <button type="button" key={label} aria-pressed={index === selected} onClick={() => selectExample(index)}>
                  <Icon aria-hidden="true" />{label}
                </button>
              ))}
            </div>
            <div className="os-demo">
              <div className="os-demo-top"><CubeIcon aria-hidden="true" className="os-mark" weight="duotone" /> Agentic OS <span className="os-sample">Sample run</span></div>
              <div className="os-chat" aria-live="polite">
                <p className="os-bubble">{example.prompt}</p>
                <div className="os-response">
                  <CubeIcon aria-hidden="true" className="os-mark" weight="duotone" />
                  <div>
                    <p>{example.result}</p>
                    <div className="os-output"><CheckIcon aria-hidden="true" weight="bold" /> {example.output}</div>
                  </div>
                </div>
              </div>
              <div className="os-demo-bottom">
                <button type="button" aria-expanded={showChecks} aria-controls="sample-checks" onClick={() => setShowChecks(!showChecks)}>
                  {showChecks ? 'Hide sample checks' : 'View sample checks'} {showChecks ? <MinusIcon aria-hidden="true" /> : <PlusIcon aria-hidden="true" />}
                </button>
                <ul id="sample-checks" hidden={!showChecks}>
                  {example.checks.map(check => <li key={check}>{check}</li>)}
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section className="os-wrap os-centered" id="workflow">
          <span className="os-kicker">Inside the workspace</span>
          <h2>From contact history to next action</h2>
          <p>Work with leads, companies, activities, and tasks in the CRM. Use Build Studio to explore dashboard drafts for sales, expenses, and inventory.</p>
          <div className="os-capabilities">
            {capabilities.map(([Icon, title, copy]) => (
              <article key={title}><span className="os-tile" aria-hidden="true"><Icon /></span><div><h3>{title}</h3><p>{copy}</p></div></article>
            ))}
          </div>
        </section>

        <section className="os-rule" id="prompts">
          <div className="os-wrap">
            <span className="os-kicker">Try a prompt</span>
            <h2>Start with a workflow you already do</h2>
            <p>Choose an example to see its sample output.</p>
            <div className="os-prompts">
              {examples.map(({ Icon, label, prompt }, index) => (
                <a href="#demo" key={label} onClick={() => selectExample(index)}>
                  <span className="os-tile" aria-hidden="true"><Icon /></span>
                  <blockquote>“{prompt}”</blockquote>
                  <span className="os-prompt-label">{label}<ArrowUpRightIcon aria-hidden="true" /></span>
                </a>
              ))}
            </div>
          </div>
        </section>

        <section className="os-wash os-band os-centered">
          <div className="os-wrap">
            <h2>Ready to build your own workflow?</h2>
            <p>Sign in with your invited account to open the workspace.</p>
            <a className="os-button os-primary" href="/login">Sign in to Agentic OS <ArrowUpRightIcon aria-hidden="true" /></a>
          </div>
        </section>

        <section className="os-wrap os-split">
          <div>
            <span className="os-kicker">Generation and testing</span>
            <h2>See how the tool was built</h2>
            <p>Inspect the prompts, attempts, and QA results. When a check fails, the agent can use the test output to try up to two repairs.</p>
          </div>
          <ol className="os-trace" aria-label="Illustrative run trace">
            <li><span>01</span>Generate a Python tool</li>
            <li><span>02</span>Test it in Docker</li>
            <li><span>03</span>Present the tool for review</li>
          </ol>
        </section>

        <section className="os-rule" id="controls">
          <div className="os-wrap">
            <span className="os-kicker">Review and control</span>
            <h2>You decide what runs</h2>
            <div className="os-controls">
              <article><div className="os-art"><span>code</span><ShieldCheckIcon aria-hidden="true" size="1.3em" /><span>QA</span></div><h3>Isolated execution</h3><p>Generated Python runs in a restricted Docker container using a limited snapshot of CRM data.</p></article>
              <article><div className="os-art"><span>Draft</span><ArrowRightIcon aria-hidden="true" size="1.3em" /><span>Review</span></div><h3>Reviewer activation</h3><p>Inspect the tool and its test results before activating a version for the workspace.</p></article>
              <article><div className="os-art"><span>v2</span><ArrowArcLeftIcon aria-hidden="true" size="1.3em" /><span>v1</span></div><h3>Version rollback</h3><p>Restore an earlier tool version when you need to revert the active automation.</p></article>
            </div>
          </div>
        </section>

        <section className="os-wrap os-faq" id="faq">
          <h2>Frequently asked questions</h2>
          <details><summary>Can I try it without an account?</summary><p>Yes. The landing page preview uses sample data. The CRM and Build Studio require an invited account.</p></details>
          <details><summary>When does an automation change CRM records?</summary><p>After a reviewer activates and runs it, the API validates its proposed changes before saving them.</p></details>
          <details><summary>What happens if testing fails?</summary><p>The agent can try up to two repairs. If the checks still fail, the run stops and shows the failure.</p></details>
        </section>
      </main>
      <footer className="os-footer">
        <div className="os-wrap">
          <div className="os-footer-links"><Wordmark /><a href="#demo">Demo</a><a href="#workflow">Workflow</a><a href="#prompts">Use cases</a><a href="#faq">FAQ</a><a href="/login">Sign in</a></div>
          <div className="os-footer-type" aria-hidden="true">Agentic OS</div>
          <small>© Agentic OS</small>
        </div>
      </footer>
    </div>
  )
}
