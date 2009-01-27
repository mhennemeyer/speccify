require File.dirname(__FILE__) + "/../test_helper.rb"

describe "change {something}" do
  before do
    @something = 1
  end
  
  it "should" do
    lambda {@something += 1}.should change {@something}
  end
  
  it "should_not" do
    lambda { }.should_not change {@something}
  end
end

describe "change {numerical}.by(number)" do
  before do
    @numerical = 1
  end
  
  it "should" do
    lambda {@numerical += 1}.should change {@numerical}.by(1)
  end
  
  it "should_not" do
    lambda {@numerical += 1}.should_not change {@numerical}.by(2)
  end
end

describe "change {numerical}.by_at_least(number)" do
  before do
    @numerical = 1
  end
  
  it "should" do
    lambda {@numerical += 3}.should change {@numerical}.by_at_least(1)
    lambda {@numerical += 3}.should change {@numerical}.by_at_least(2)
    lambda {@numerical += 3}.should change {@numerical}.by_at_least(3)
  end
  
  it "should_not" do
    lambda {@numerical += 1}.should_not change {@numerical}.by_at_least(2)
  end
end

describe "change {numerical}.by_at_most(number)" do
  before do
    @numerical = 1
  end
  
  it "should" do
    lambda {@numerical += 1}.should change {@numerical}.by_at_most(1)
    lambda {@numerical += 1}.should change {@numerical}.by_at_most(2)
    lambda {@numerical += 1}.should change {@numerical}.by_at_most(3)
  end
  
  it "should_not" do
    lambda {@numerical += 3}.should_not change {@numerical}.by_at_most(1)
    lambda {@numerical += 3}.should_not change {@numerical}.by_at_most(2)
  end
end

describe "change {numerical}.from(first).to(second_value)" do
  before do
    @numerical = 1
  end
  
  it "should" do
    lambda {@numerical += 1}.should change {@numerical}.from(1).to(2)
  end
  
  it "should_not" do
    lambda {@numerical += 3}.should_not change {@numerical}.from(1).to(3)
    lambda {@numerical += 3}.should_not change {@numerical}.from(2).to(4)
  end
end

