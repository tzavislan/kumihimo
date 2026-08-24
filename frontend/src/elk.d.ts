/**
 * @file        frontend/src/elk.d.ts
 * @purpose     Types for the bundled elkjs entry point, which ships without its
 *              own declaration for this subpath.
 * @layer       frontend
 * @tags        elkjs, declarations
 * @related     frontend/src/layout.ts (the only importer)
 * @design      PLAN.md §8
 */
declare module "elkjs/lib/elk.bundled.js" {
  import ELK from "elkjs";
  export default ELK;
}
