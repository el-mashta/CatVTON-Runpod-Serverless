# Load Balancing Endpoint Test Results

## Executive Summary

The load balancing and worker architecture is fundamentally sound and performs as expected under light concurrent load. The tests reveal that the system correctly scales by provisioning multiple workers when requests arrive in parallel.

However, the 30-request test uncovered a **client-side bottleneck** in the test script itself, which prevented a true high-concurrency stress test. The failures observed (`400 Bad Request`) were a direct result of this client-side issue, not a failure of the RunPod service.

## Test 1: 3 Concurrent Requests

This test was a complete success and demonstrates the core functionality of the load balancing endpoint.

### Observations:
- **Successful Scaling:** The RunPod logs clearly show that two distinct workers (`q1j33s08lgn2gs` and `4de7ae5c4x293f`) were provisioned to handle the three concurrent requests.
- **Parallel Processing:** All three requests were processed successfully and in parallel, with completion times spread out as expected while the new workers came online.
- **No Errors:** All requests returned a `200 OK` status.

**Conclusion:** The system correctly handles concurrent traffic by scaling up the number of active workers.

## Test 2: 30 Concurrent Requests

This test successfully processed many requests but ultimately failed due to limitations in the test script, not the endpoint.

### Observations:
1.  **Client-Side S3 Bottleneck:** The test script log shows multiple warnings: `Connection pool is full, discarding connection: s3api-eu-ro-1.runpod.io`. The script attempts to upload all 30 sets of images to S3 simultaneously, overwhelming the default connection limit (10) of the `boto3` S3 client.
2.  **Sequential Request Arrival:** Due to the S3 bottleneck, the requests did not arrive at the RunPod endpoint concurrently. Instead, they were effectively queued on the client side and sent one after another as S3 uploads completed.
3.  **Single Worker Provisioned:** Because the requests arrived sequentially, the RunPod load balancer correctly determined that only a single worker (`4de7ae5c4x293f`) was needed to handle the load. The RunPod logs show this single worker processing many requests back-to-back.
4.  **Request Timeouts:** Towards the end of the test, multiple requests failed with a `400 Bad Request`. This is because the single worker was still busy with earlier requests. The new requests waited in the load balancer's queue for longer than the maximum timeout period (2 minutes) and were subsequently rejected.

### Conclusion:
The failures in the 30-request test were not caused by the RunPod endpoint's inability to scale, but by the test script's inability to send requests truly concurrently. The script inadvertently created a long queue that led to timeouts. The RunPod infrastructure behaved exactly as it should based on the sequential traffic it received.

To perform a true high-concurrency test, the test script would need to be modified to manage its S3 connection pool more effectively, for example by using a semaphore to limit concurrent uploads.
