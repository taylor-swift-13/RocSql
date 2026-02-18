(* This program is free software; you can redistribute it and/or      *)
(* modify it under the terms of the GNU Lesser General Public License *)
(* as published by the Free Software Foundation; either version 2.1   *)
(* of the License, or (at your option) any later version.             *)
(*                                                                    *)
(* This program is distributed in the hope that it will be useful,    *)
(* but WITHOUT ANY WARRANTY; without even the implied warranty of     *)
(* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the      *)
(* GNU Lesser General Public License for more details.                *)
(*                                                                    *)
(* You should have received a copy of the GNU Lesser General Public   *)
(* License along with this program; if not, write to the Free         *)
(* Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA *)
(* 02110-1301 USA                                                     *)

(** * Uniqueness of keys in association lists

- Key definitions: [unique_key]
- Initial author: Laurent.Thery@inria.fr (2003)

*)

From Coq Require Import Sorting.Permutation.
From Huffman Require Export AuxLib.

Set Default Proof Using "Type".

Section UniqueKey.
Variables (A : Type) (B : Type).

#[local] Hint Constructors Permutation : core.
#[local] Hint Resolve Permutation_refl : core.
#[local] Hint Resolve Permutation_app : core.
#[local] Hint Resolve Permutation_app_swap : core.

(** An association list has unique keys if the keys appear only once *)
Inductive unique_key : list (A * B) -> Prop :=
  | unique_key_nil : unique_key []
  | unique_key_cons :
      forall (a : A) (b : B) l,
      (forall b : B, ~ In (a, b) l) ->
      unique_key l -> unique_key ((a, b) :: l).
#[local] Hint Constructors unique_key : core.
 
(** Inversion theorem for unique keys *)
Theorem unique_key_inv : forall a l, unique_key (a :: l) -> unique_key l.
Proof.  
intros a l H; inversion H; auto.
Qed.

(** Inversion theorem for unique keys *)
Theorem unique_key_in :
 forall (a : A) (b1 b2 : B) l, unique_key ((a, b1) :: l) -> ~ In (a, b2) l.
Proof.
intros a b l H b''.
  inversion H as [H_not_in | _].
  apply H_not_in
Qed.
