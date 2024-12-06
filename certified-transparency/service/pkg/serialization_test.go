package pkg

import (
	"certified-transparency/pkg/models"
	"crypto/ed25519"
	"fmt"
	"testing"
	"time"
)

var ownership = models.Ownership{
	ContentHash: [32]byte{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16},
	Name:        "TestName",
}

var sot = models.SignedOwnershipTimestamp{
	Timestamp: time.Now(),
	Ownership: ownership,
	Signature: []byte{},
}

var sth = models.SignedTreeHead{
	Size:      123,
	Timestamp: time.Now(),
	Hash:      [32]byte{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16},
	Signature: []byte{},
}

var leaf = models.TreeLeaf{
	Created:              time.Now(),
	Ownership:            ownership,
	PubKey:               make(ed25519.PublicKey, 32),
	DataForPrivateClaims: []byte{1, 2, 3},
	DataForPublicClaims:  []byte{1, 2, 3, 4, 5, 6},
}

var leafProof = models.TreeLeafProof{
	Head:  sth,
	Index: 3,
	Leaf:  leaf,
	Hashes: [][32]byte{
		[32]byte{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16},
		[32]byte{0xff, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16},
	},
}

func TestOwnershipSerialize(t *testing.T) {
	data := ownership.Serialize()
	ownership2 := models.UnserializeOwnership(data)
	if ownership != ownership2 {
		t.FailNow()
	}
}

func TestSignedOwnershipTimestampSerialize(t *testing.T) {
	pubkey, privkey, _ := ed25519.GenerateKey(nil)

	SignOwnership(privkey, &sot)
	data := sot.Serialize()
	sot2, err := models.UnserializeSignedOwnershipTimestamp(data)
	if err != nil {
		t.Error(err)
		t.FailNow()
	}
	if fmt.Sprintf("%#v", sot) != fmt.Sprintf("%#v", sot2) {
		t.Errorf("Not equal!\n%#v\n%#v\n", sot, sot2)
		t.FailNow()
	}
	if !VerifyOwnership(pubkey, &sot2) {
		t.FailNow()
	}
}

func TestSignedTreeHeadSerialize(t *testing.T) {
	pubkey, privkey, _ := ed25519.GenerateKey(nil)

	SignTreeHead(privkey, &sth)
	data := sth.Serialize()
	sth2, err := models.UnserializeSignedTreeHead(data)
	if err != nil {
		t.Error(err)
		t.FailNow()
	}
	if fmt.Sprintf("%#v", sth) != fmt.Sprintf("%#v", sth2) {
		t.Errorf("Not equal!\n%#v\n%#v\n", sth, sth2)
		t.FailNow()
	}
	if !VerifyTreeHead(pubkey, &sth2) {
		t.FailNow()
	}
}

func TestVulnerability2(t *testing.T) {
	pubkey, privkey, _ := ed25519.GenerateKey(nil)

	SignTreeHead(privkey, &sth)
	if !VerifyHash(pubkey, sth.Hash, sth.Signature) {
		t.Error("not vulnerable")
	}
}

func TestTreeLeafSerialize(t *testing.T) {
	data := leaf.Serialize()
	leaf2, err := models.UnserializeTreeLeaf(data)
	if err != nil {
		t.Error(err)
		t.FailNow()
	}
	if fmt.Sprintf("%#v", leaf) != fmt.Sprintf("%#v", leaf2) {
		t.FailNow()
	}
}

func TestTreeLeafProofSerialize(t *testing.T) {
	pubkey, privkey, _ := ed25519.GenerateKey(nil)

	SignTreeHead(privkey, &leafProof.Head)
	data := leafProof.Serialize()
	leafProof2, err := models.UnserializeTreeLeafProof(data)
	if err != nil {
		t.Error(err)
		t.FailNow()
	}
	if fmt.Sprintf("%#v", leafProof) != fmt.Sprintf("%#v", leafProof2) {
		t.Errorf("Not equal!\n%#v\n%#v\n", leafProof, leafProof2)
		t.FailNow()
	}
	if !VerifyTreeHead(pubkey, &leafProof2.Head) {
		t.FailNow()
	}
}
