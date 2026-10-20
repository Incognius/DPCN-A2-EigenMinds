import { useState } from "react";
import {
  flexRender, getCoreRowModel, getSortedRowModel, getPaginationRowModel,
  useReactTable, type ColumnDef, type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from "lucide-react";

/** Sortable, paginated table (click a header to sort). */
export default function DataTable<T>({ data, columns, initialSort, pageSize = 12, onRow, maxHeight }: {
  data: T[]; columns: ColumnDef<T, any>[]; initialSort?: SortingState; pageSize?: number;
  onRow?: (row: T) => void; maxHeight?: number;
}) {
  const [sorting, setSorting] = useState<SortingState>(initialSort ?? []);
  const table = useReactTable({
    data, columns, state: { sorting }, onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(), initialState: { pagination: { pageSize } },
  });
  const p = table.getState().pagination;
  return (
    <div>
      <div className="scroll-thin overflow-auto rounded-2xl border border-white/[0.05]" style={maxHeight ? { maxHeight } : undefined}>
        <table className="dt w-full border-collapse">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id} onClick={h.column.getToggleSortingHandler()} aria-sort={h.column.getIsSorted() === "asc" ? "ascending" : h.column.getIsSorted() === "desc" ? "descending" : "none"}>
                    <span className="inline-flex items-center gap-1">
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getIsSorted() === "asc" ? <ArrowUp size={12} /> : h.column.getIsSorted() === "desc" ? <ArrowDown size={12} /> : null}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((r) => (
              <tr key={r.id} onClick={() => onRow?.(r.original)} className={onRow ? "cursor-pointer" : ""}>
                {r.getVisibleCells().map((c) => <td key={c.id}>{flexRender(c.column.columnDef.cell, c.getContext())}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.getPageCount() > 1 && (
        <div className="mt-3 flex items-center justify-between text-[12.5px] text-ink-muted">
          <span>{p.pageIndex * p.pageSize + 1}–{Math.min((p.pageIndex + 1) * p.pageSize, data.length)} of {data.length}</span>
          <div className="flex gap-1.5">
            <button className="pill pill-sm" disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()} aria-label="Previous page"><ChevronLeft size={14} /></button>
            <button className="pill pill-sm" disabled={!table.getCanNextPage()} onClick={() => table.nextPage()} aria-label="Next page"><ChevronRight size={14} /></button>
          </div>
        </div>
      )}
    </div>
  );
}
