package storage

import (
	"bytes"
	"context"
	"fmt"
	"io"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

type S3Client struct {
	client     *s3.Client
	bucketName string
}

func NewS3Client(bucketName string) (*S3Client, error) {
	cfg, err := config.LoadDefaultConfig(context.Background())
	if err != nil {
		return nil, fmt.Errorf("unable to load SDK config: %w", err)
	}
	return &S3Client{
		client:     s3.NewFromConfig(cfg),
		bucketName: bucketName,
	}, nil
}

func (c *S3Client) Upload(ctx context.Context, key string, data []byte, metadata map[string]string) error {
	_, err := c.client.PutObject(ctx, &s3.PutObjectInput{
		Bucket:   &c.bucketName,
		Key:      &key,
		Body:     bytes.NewReader(data),
		Metadata: metadata,
	})
	return err
}

func (c *S3Client) Download(ctx context.Context, bucket, key string) ([]byte, error) {
	result, err := c.client.GetObject(ctx, &s3.GetObjectInput{
		Bucket: &bucket,
		Key:    &key,
	})
	if err != nil {
		return nil, err
	}
	defer result.Body.Close()
	return io.ReadAll(result.Body)
}
