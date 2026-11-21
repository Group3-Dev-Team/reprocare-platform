import { Link } from 'react-router-dom';

/** Page title band with breadcrumbs and an optional illustration or action on the right. */
export function PageHeader({ title, intro, crumbs = [], aside, children, tone = 'blue' }) {
  return (
    <header className={`page-header page-header-${tone}`}>
      <div className="container page-header-inner">
        <div className="page-header-copy">
          {crumbs.length > 0 && <Breadcrumbs items={crumbs} />}
          <h1>{title}</h1>
          {intro && <p className="lede">{intro}</p>}
          {children}
        </div>
        {aside && <div className="page-header-aside">{aside}</div>}
      </div>
    </header>
  );
}

export function Breadcrumbs({ items }) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <ol itemScope itemType="https://schema.org/BreadcrumbList">
        {[{ label: 'Home', to: '/' }, ...items].map((item, index) => (
          <li
            key={`${index}-${item.label}`}
            aria-current={index === items.length ? 'page' : undefined}
            itemProp="itemListElement"
            itemScope
            itemType="https://schema.org/ListItem"
          >
            {item.to && index !== items.length ? (
              <Link to={item.to} itemProp="item"><span itemProp="name">{item.label}</span></Link>
            ) : (
              <span itemProp="name">{item.label}</span>
            )}
            <meta itemProp="position" content={index + 1} />
          </li>
        ))}
      </ol>
    </nav>
  );
}
