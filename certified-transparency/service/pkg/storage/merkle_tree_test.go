package storage

import (
	"bytes"
	"certified-transparency/pkg/models"
	"crypto/ed25519"
	"fmt"
	"testing"
	"time"
)

var leaves = []models.TreeLeaf{
	{
		Created: time.Now(),
		Ownership: models.Ownership{
			Name: "leaf1",
		},
		PubKey:               make(ed25519.PublicKey, 0),
		DataForPrivateClaims: []byte("a"),
		DataForPublicClaims:  []byte("b"),
	},
	{
		Created: time.Now(),
		Ownership: models.Ownership{
			Name: "leaf2",
		},
		PubKey:               make(ed25519.PublicKey, 0),
		DataForPrivateClaims: []byte("aaa"),
		DataForPublicClaims:  []byte("bbbb"),
	},
	{
		Created: time.Now(),
		Ownership: models.Ownership{
			Name: "leaf3",
		},
		PubKey:               make(ed25519.PublicKey, 0),
		DataForPrivateClaims: []byte("aaa"),
		DataForPublicClaims:  []byte("bbbb"),
	},
	{
		Created: time.Now(),
		Ownership: models.Ownership{
			Name: "leaf4",
		},
		PubKey:               make(ed25519.PublicKey, 0),
		DataForPrivateClaims: []byte("aaa"),
		DataForPublicClaims:  []byte("bbbb"),
	},
	{
		Created: time.Now(),
		Ownership: models.Ownership{
			Name: "leaf5",
		},
		PubKey:               make(ed25519.PublicKey, 0),
		DataForPrivateClaims: []byte("aaa"),
		DataForPublicClaims:  []byte("bbbb"),
	},
}

func TestMerkleTree_Append(t *testing.T) {
	repo := OpenInMemoryRepository()
	defer repo.db.Close()
	tree := NewMerkleTree(repo)

	for i, leaf := range leaves {
		if tree.Size() != uint64(i) {
			t.Errorf("size of tree should be 0, got %d", tree.Size())
		}
		index, err := tree.Append(leaf)
		if err != nil {
			t.Error(err)
			t.FailNow()
		}
		if uint64(i) != index {
			t.Errorf("index should be %d, got %d", i, index)
		}
		if tree.Size() != uint64(i)+1 {
			t.Errorf("size of tree should be 1, got %d", tree.Size())
		}
	}

	// retrieve items
	for i, leaf := range leaves {
		leaf2, err := tree.GetLeaf(uint64(i))
		if err != nil {
			t.Error(err)
			t.FailNow()
		}
		if fmt.Sprintf("%#v", leaf) != fmt.Sprintf("%#v", *leaf2) {
			t.Errorf("leaf should be %v, got %v", leaf, *leaf2)
		}
	}
}

func TestMerkleTree_Head(t *testing.T) {
	repo := OpenInMemoryRepository()
	defer repo.db.Close()
	tree := NewMerkleTree(repo)

	sth := tree.Head()
	if sth.Size != 0 {
		t.Errorf("tree size should be 0, got %d", tree.Size())
	}
	if !bytes.Equal(sth.Hash[:], make([]byte, 32)) {
		t.Errorf("tree hash is %x", sth.Hash)
	}

	for _, leaf := range leaves {
		_, err := tree.Append(leaf)
		if err != nil {
			t.Error(err)
			t.FailNow()
		}
	}

	sth = tree.Head()
	if sth.Size != uint64(len(leaves)) {
		t.Errorf("tree size should be %d, got %d", len(leaves), tree.Size())
	}
}

func TestMerkleTree_GetLeafProof(t *testing.T) {
	repo := OpenInMemoryRepository()
	defer repo.db.Close()
	tree := NewMerkleTree(repo)

	for _, leaf := range leaves {
		_, err := tree.Append(leaf)
		if err != nil {
			t.Error(err)
			t.FailNow()
		}
	}

	head := tree.Head()

	for i, leaf := range leaves {
		proof, err := tree.GetLeafProof(uint64(i))
		if err != nil {
			t.Error(err)
			t.FailNow()
		}
		if fmt.Sprintf("%#v", proof.Leaf) != fmt.Sprintf("%#v", leaf) {
			t.Errorf("leaf should be %v, got %v", leaf, proof.Leaf)
		}
		if proof.Index != uint64(i) {
			t.Errorf("index should be %d, got %d", i, proof.Index)
		}
		if proof.Head.Size != uint64(len(leaves)) {
			t.Errorf("proof head size should be %d, got %d", len(leaves), proof.Head.Size)
		}
		if !bytes.Equal(proof.Head.Hash[:], head.Hash[:]) {
			t.Errorf("proof head should be %v, got %v", head, proof.Head)
		}

		if !VerifyLeafProofHashes(proof) {
			t.Errorf("leaf proof is not verifiable")
		}
	}
}
