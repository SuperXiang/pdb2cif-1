#!/usr/bin/env python
# Copyright (C) 2021-Present  Elija Feigl
# Full GPL-3 License can be found in `LICENSE` at the project root.
""" files module
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
from typing import TYPE_CHECKING

from .. import get_resource
from .types import ChainID
from .types import ResName

if TYPE_CHECKING:
    from .structure import Structure


@dataclass
class PDB:
    """atomic format PDB"""

    struct: Structure

    def __post_init__(self):
        # TODO-low: get box from struct
        self.box = "1000.000 1000.000 1000.000"

    def _header(self) -> list[str]:
        return ["HEADER   "]

    def _authors(self) -> list[str]:
        return ["AUTHOR   "]

    def _remarks(self) -> list[str]:
        return ["REMARK   "]

    def _box(self) -> list[str]:
        angles = "90.00  90.00  90.00"
        space_group = "P 1"
        z_value = "1"
        return [f"CRYST1 {self.box}  {angles} {space_group}           {z_value}"]

    def _atoms(self) -> list[str]:
        return [atom.as_pdb() for atom in self.struct.atoms]

    def write(self, outfile: Path) -> None:
        """write pdb file"""
        with open(outfile, mode="w+") as out_file:
            for part in [
                self._header(),
                self._authors(),
                self._remarks(),
                self._box(),
                self._atoms(),
            ]:
                out_file.writelines(part)


@dataclass
class CIF:
    struct: Structure

    def __post_init__(self):
        self.atoms: list[str] = self._set_atoms()
        self.chains, self.seqs = self._get_chains_seqs()

    def _set_atoms(self) -> list[str]:
        return [atom.as_cif() for atom in self.struct.atoms]

    def _get_chains_seqs(self) -> tuple[dict[int, int], dict[int, list[ResName]]]:
        chains: dict[int, int] = dict()
        seqs: dict[int, list[ResName]] = dict()
        C3ps = [a for a in self.struct.atoms if a.atom_name.as_str() == "C3'"]
        for a in C3ps:
            chain_id = a.chain_id.n
            res_number = a.res_number.n

            if chain_id not in chains:
                chains[chain_id] = res_number
            elif res_number > chains[chain_id]:
                chains[chain_id] = res_number

            if chain_id not in seqs:  # only res not atom
                seqs[chain_id] = [a.res_name]
            else:
                seqs[chain_id].append(a.res_name)

        return chains, seqs

    def _write_atoms(self, file_out: TextIO) -> None:
        atom_header = get_resource("cif_templates/atom_header.txt").read_text()
        file_out.write(atom_header)
        file_out.writelines(self.atoms)

    def _write_header(self, file_out: TextIO) -> None:
        header = get_resource("cif_templates/header.txt").read_text()
        file_out.write(f"data_{self.struct.name}\n")
        file_out.write(header)

    def _write_pdbx_struct(self, file_out: TextIO) -> None:
        pdbx_struct = get_resource("cif_templates/pdbx_struct.txt").read_text()
        pdbx_struct = pdbx_struct.replace("NCHAINS", str(len(self.chains)))
        file_out.write(pdbx_struct)

    def _write_entity(self, file_out: TextIO) -> None:
        entity = get_resource("cif_templates/entity.txt").read_text()
        file_out.write(entity)
        for chain_id, length in self.chains.items():
            is_staple = length < 500
            n = str(chain_id).ljust(4)
            src = "syn" if is_staple else "?  "
            typ = "'STAPLE STRAND'  " if is_staple else "'SCAFFOLD STRAND'"
            file_out.write(f"{n} polymer {src} {typ} ?   1 ? ? ? ?\n")

    def _write_entity_src(self, file_out: TextIO) -> None:
        entity_src = get_resource("cif_templates/entity_src.txt").read_text()
        file_out.write(entity_src)
        for chain_id, length in self.chains.items():
            is_staple = length < 500
            n = str(chain_id).ljust(4)
            typ = "'synthetic construct'" if is_staple else "?".ljust(21)
            tax = "32630" if is_staple else "?".ljust(5)
            file_out.write(f"{n}   1 sample 1 {str(length).ljust(5)} {typ} ? {tax} ?\n")

    def _write_entity_poly(self, file_out: TextIO) -> None:
        entity_poly = get_resource("cif_templates/entity_poly.txt").read_text()
        file_out.write(entity_poly)
        for chain_id, seq in self.seqs.items():
            n = str(chain_id).ljust(4)
            cid = ChainID(chain_id).as_chimera()
            seq1 = "".join([f"({s.as_str()})" for s in seq])
            seq2 = "".join([s.as_X() for s in seq])
            file_out.write(f"{n} polydeoxyribonucleotide no no\n;{seq1}\n;\n{seq2} {cid} ?\n")

    def write(self, outfile: Path) -> None:
        with open(outfile, mode="w+") as file_out:
            self._write_header(file_out)
            self._write_pdbx_struct(file_out)
            self._write_atoms(file_out)
            self._write_entity(file_out)
            self._write_entity_src(file_out)
            self._write_entity_poly(file_out)
