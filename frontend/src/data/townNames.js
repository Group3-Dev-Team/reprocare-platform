/** The directory API groups towns by county. Town-only filters need one option per name. */
export function townNames(rows = []) {
  const names = rows.map(({ town }) => town).filter((town) => typeof town === 'string' && town.trim());
  return [...new Map(names.map((town) => [town.toLocaleLowerCase(), town])).values()]
    .sort((first, second) => first.localeCompare(second));
}
