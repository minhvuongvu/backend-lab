package lab.{{PKG}}.contract;

import org.springframework.test.context.ActiveProfiles;

@ActiveProfiles("before")
class BeforeContractTest extends ItemServiceContractTest {

    @Override
    protected String expectedImplementation() {
        return "before";
    }
}
